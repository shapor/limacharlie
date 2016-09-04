/*
Copyright 2015 refractionPOINT

Licensed under the Apache License, Version 2.0 ( the "License" );
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http ://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

#include <rpal/rpal.h>
#include <rpHostCommonPlatformIFaceLib/rpHostCommonPlatformIFaceLib.h>

#include <processLib/processLib.h>
#include <rpHostCommonPlatformLib/rTags.h>
#include <obfuscationLib/obfuscationLib.h>
#include <notificationsLib/notificationsLib.h>
#include <cryptoLib/cryptoLib.h>
#include <librpcm/librpcm.h>
#include <kernelAcquisitionLib/kernelAcquisitionLib.h>
#include "collectors.h"
#include "keys.h"
#include "git_info.h"
#include <libOs/libOs.h>

#ifdef RPAL_PLATFORM_MACOSX
#include <Security/Authorization.h>
#endif

//=============================================================================
//  RP HCP Module Requirements
//=============================================================================
#define RPAL_FILE_ID 82
RpHcp_ModuleId g_current_Module_id = 2;

//=============================================================================
//  Global Behavior Variables
//=============================================================================
#define HBS_EXFIL_QUEUE_MAX_NUM                 5000
#define HBS_EXFIL_QUEUE_MAX_SIZE                (1024*1024*10)
#define HBS_MAX_OUBOUND_FRAME_SIZE              (100)
#define HBS_SYNC_INTERVAL                       (60*5)

// Large blank buffer to be used to patch configurations post-build
#define _HCP_DEFAULT_STATIC_STORE_SIZE                          (1024 * 50)
#define _HCP_DEFAULT_STATIC_STORE_MAGIC                         { 0xFA, 0x57, 0xF0, 0x0D }
static RU8 g_patchedConfig[ _HCP_DEFAULT_STATIC_STORE_SIZE ] = _HCP_DEFAULT_STATIC_STORE_MAGIC;
#define _HCP_DEFAULT_STATIC_STORE_KEY                           { 0xFA, 0x75, 0x01 }

//=============================================================================
//  Global Context
//=============================================================================
HbsState g_hbs_state = { NULL,
                         NULL,
                         NULL,
                         NULL,
                         { 0 },
                         0,
                         0,
                         NULL,
                         { ENABLED_COLLECTOR( 0 ),
                           ENABLED_COLLECTOR( 1 ),
                           ENABLED_WINDOWS_COLLECTOR( 2 ),
                           ENABLED_COLLECTOR( 3 ),
                           ENABLED_WINDOWS_COLLECTOR( 4 ),
                           ENABLED_WINDOWS_COLLECTOR( 5 ),
                           ENABLED_COLLECTOR( 6 ),
                           DISABLED_LINUX_COLLECTOR( 7 ),
                           ENABLED_COLLECTOR( 8 ),
                           ENABLED_COLLECTOR( 9 ),
                           ENABLED_COLLECTOR( 10 ),
                           ENABLED_COLLECTOR( 11 ),
                           DISABLED_COLLECTOR( 12 ),
                           ENABLED_WINDOWS_COLLECTOR( 13 ),
                           DISABLED_COLLECTOR( 14 ),
                           DISABLED_OSX_COLLECTOR( 15 ),
                           ENABLED_COLLECTOR( 16 ),
                           ENABLED_COLLECTOR( 17 ),
                           DISABLED_LINUX_COLLECTOR( 18 ),
                           ENABLED_COLLECTOR( 19 ),
                           ENABLED_COLLECTOR( 20 ) } };
RU8* hbs_cloud_pub_key = hbs_cloud_default_pub_key;

//=============================================================================
//  Utilities
//=============================================================================
static
rSequence
    getStaticConfig
    (

    )
{
    RU8 magic[] = _HCP_DEFAULT_STATIC_STORE_MAGIC;
    rSequence config = NULL;
    RU32 unused = 0;
    RU8 key[] = _HCP_DEFAULT_STATIC_STORE_KEY;

    if( 0 != rpal_memory_memcmp( g_patchedConfig, magic, sizeof( magic ) ) )
    {
        obfuscationLib_toggle( g_patchedConfig, sizeof( g_patchedConfig ), key, sizeof( key ) );

        if( rSequence_deserialise( &config, g_patchedConfig, sizeof( g_patchedConfig ), &unused ) )
        {
            rpal_debug_info( "static store patched, using it as config" );
        }

        obfuscationLib_toggle( g_patchedConfig, sizeof( g_patchedConfig ), key, sizeof( key ) );
    }
    else
    {
        rpal_debug_info( "static store not patched, using defaults" );
    }

    return config;
}

#ifdef RPAL_PLATFORM_WINDOWS
static RBOOL
    WindowsSetPrivilege
    (
        HANDLE hToken,
        LPCTSTR lpszPrivilege,
        BOOL bEnablePrivilege
    )
{
    LUID luid;
    RBOOL bRet = FALSE;

    if( LookupPrivilegeValue( NULL, lpszPrivilege, &luid ) )
    {
        TOKEN_PRIVILEGES tp;

        tp.PrivilegeCount = 1;
        tp.Privileges[ 0 ].Luid = luid;
        tp.Privileges[ 0 ].Attributes = ( bEnablePrivilege ) ? SE_PRIVILEGE_ENABLED : 0;
        //
        //  Enable the privilege or disable all privileges.
        //
        if( AdjustTokenPrivileges( hToken, FALSE, &tp, 0, (PTOKEN_PRIVILEGES)NULL, (PDWORD)NULL ) )
        {
            //
            //  Check to see if you have proper access.
            //  You may get "ERROR_NOT_ALL_ASSIGNED".
            //
            bRet = ( GetLastError() == ERROR_SUCCESS );
        }
    }
    return bRet;
}


static RBOOL
    WindowsGetPrivilege
    (
        RPCHAR privName
    )
{
    RBOOL isSuccess = FALSE;

    HANDLE hProcess = NULL;
    HANDLE hToken = NULL;

    hProcess = GetCurrentProcess();

    if( NULL != hProcess )
    {
        if( OpenProcessToken( hProcess, TOKEN_ADJUST_PRIVILEGES, &hToken ) )
        {
            if( WindowsSetPrivilege( hToken, privName, TRUE ) )
            {
                isSuccess = TRUE;
            }

            CloseHandle( hToken );
        }
    }

    return isSuccess;
}
#endif

static 
RBOOL
    getPrivileges
    (

    )
{
    RBOOL isSuccess = FALSE;

#ifdef RPAL_PLATFORM_WINDOWS
    RCHAR strSeDebug[] = "SeDebugPrivilege";
    RCHAR strSeBackup[] = "SeBackupPrivilege";
    RCHAR strSeRestore[] = "SeRestorePrivilege";
    if( !WindowsGetPrivilege( strSeDebug ) )
    {
        rpal_debug_warning( "error getting SeDebugPrivilege" );
    }
    if( !WindowsGetPrivilege( strSeBackup ) )
    {
        rpal_debug_warning( "error getting SeBackupPrivilege" );
    }
    if( !WindowsGetPrivilege( strSeRestore ) )
    {
        rpal_debug_warning( "error getting SeRestorePrivilege" );
    }
#elif defined( RPAL_PLATFORM_LINUX )
    
#elif defined( RPAL_PLATFORM_MACOSX )
    /*
    OSStatus stat;
    AuthorizationItem taskport_item[] = {{"system.privilege.taskport:"}};
    AuthorizationRights rights = {1, taskport_item}, *out_rights = NULL;
    AuthorizationRef author;
    
    AuthorizationFlags auth_flags = kAuthorizationFlagExtendRights | 
                                    kAuthorizationFlagPreAuthorize | 
                                    ( 1 << 5);

    stat = AuthorizationCreate( NULL, kAuthorizationEmptyEnvironment, auth_flags, &author );
    if( stat != errAuthorizationSuccess )
    {
        isSuccess = TRUE;
    }
    else
    {
        stat = AuthorizationCopyRights( author, 
                                        &rights, 
                                        kAuthorizationEmptyEnvironment, 
                                        auth_flags, 
                                        &out_rights );
        if( stat == errAuthorizationSuccess )
        {
            isSuccess = TRUE;
        }
    }
    */
#endif

    return isSuccess;
}

static RVOID
    freeExfilEvent
    (
        rSequence seq,
        RU32 unused
    )
{
    UNREFERENCED_PARAMETER( unused );
    rSequence_free( seq );
}


static RBOOL
checkKernelAcquisition
(

)
{
    RBOOL isKernelInit = FALSE;

    if( !kAcq_init() )
    {
        rpal_debug_info( "kernel acquisition not initialized" );
    }
    else
    {
        if( kAcq_ping() )
        {
            rpal_debug_info( "kernel acquisition available" );
            isKernelInit = TRUE;
        }
        else
        {
            rpal_debug_info( "kernel acquisition not available" );
            kAcq_deinit();
        }
    }

    return isKernelInit;
}

static RBOOL
    updateCollectorConfigs
    (
        rList newConfigs
    )
{
    RBOOL isSuccess = FALSE;
    RU8 unused = 0;
    RU32 i = 0;
    rSequence tmpConf = NULL;
    RU32 confId = 0;

    if( rpal_memory_isValid( newConfigs ) )
    {
        rpal_debug_info( "updating collector configurations." );
        
        for( i = 0; i < ARRAY_N_ELEM( g_hbs_state.collectors ); i++ )
        {
            if( NULL != g_hbs_state.collectors[ i ].conf )
            {
                rpal_debug_info( "freeing collector %d config.", i );
                rSequence_free( g_hbs_state.collectors[ i ].conf );
                g_hbs_state.collectors[ i ].conf = NULL;
            }
        }

        while( rList_getSEQUENCE( newConfigs, RP_TAGS_HBS_CONFIGURATION, &tmpConf ) )
        {
            if( rSequence_getRU32( tmpConf, RP_TAGS_HBS_CONFIGURATION_ID, &confId ) &&
                confId < ARRAY_N_ELEM( g_hbs_state.collectors ) )
            {
                if( rSequence_getRU8( tmpConf, RP_TAGS_IS_DISABLED, &unused ) )
                {
                    g_hbs_state.collectors[ confId ].isEnabled = FALSE;
                }
                else
                {
                    g_hbs_state.collectors[ confId ].isEnabled = TRUE;
                    g_hbs_state.collectors[ confId ].conf = rSequence_duplicate( tmpConf );
                    rpal_debug_info( "set new collector %d config.", confId );
                }
            }
        }
                
        isSuccess = TRUE;
    }

    return isSuccess;
}

static RVOID
    shutdownCollectors
    (

    )
{
    RU32 i = 0;

    if( !rEvent_wait( g_hbs_state.isTimeToStop, 0 ) )
    {
        rpal_debug_info( "signaling to collectors to stop." );
        rEvent_set( g_hbs_state.isTimeToStop );

        if( NULL != g_hbs_state.hThreadPool )
        {
            rpal_debug_info( "destroying collector thread pool." );
            rThreadPool_destroy( g_hbs_state.hThreadPool, TRUE );
            g_hbs_state.hThreadPool = NULL;

            for( i = 0; i < ARRAY_N_ELEM( g_hbs_state.collectors ); i++ )
            {
                if( g_hbs_state.collectors[ i ].isEnabled )
                {
                    rpal_debug_info( "cleaning up collector %d.", i );
                    g_hbs_state.collectors[ i ].cleanup( &g_hbs_state, g_hbs_state.collectors[ i ].conf );
                    rSequence_free( g_hbs_state.collectors[ i ].conf );
                    g_hbs_state.collectors[ i ].conf = NULL;
                }
            }
        }
    }
}

static
RBOOL
    sendSingleMessageHome
    (
        rSequence message
    )
{
    RBOOL isSuccess = FALSE;

    rList messages = NULL;

    if( NULL != ( messages = rList_new( RP_TAGS_MESSAGE, RPCM_SEQUENCE ) ) )
    {
        if( rSequence_addSEQUENCE( messages, RP_TAGS_MESSAGE, message ) )
        {
            isSuccess = rpHcpI_sendHome( messages );
        }

        rList_shallowFree( messages );
    }

    return isSuccess;
}


static
RPVOID
RPAL_THREAD_FUNC
    issueSync
    (
        rEvent isTimeToStop,
        RPVOID ctx
    )
{
    rSequence wrapper = NULL;
    rSequence message = NULL;

    rThreadPoolTask* tasks = NULL;
    RU32 nTasks = 0;
    RU32 i = 0;
    rList taskList = NULL;
    rSequence task = NULL;
    RTIME threadTime = 0;

    UNREFERENCED_PARAMETER( ctx );

    if( rEvent_wait( isTimeToStop, 0 ) )
    {
        return NULL;
    }

    rpal_debug_info( "issuing sync to cloud" );

    if( NULL != ( wrapper = rSequence_new() ) )
    {
        if( NULL != ( message = rSequence_new() ) )
        {
            if( rSequence_addSEQUENCE( wrapper, RP_TAGS_NOTIFICATION_SYNC, message ) )
            {
                if( rSequence_addBUFFER( message,
                                         RP_TAGS_HASH,
                                         g_hbs_state.currentConfigHash,
                                         sizeof( g_hbs_state.currentConfigHash ) ) )
                {
                    // The current version running.
                    rSequence_addRU32( message, RP_TAGS_PACKAGE_VERSION, GIT_REVISION );

                    // Is kernel acquisition currently available?
                    rSequence_addRU8( message, RP_TAGS_HCP_KERNEL_ACQ_AVAILABLE, (RU8)checkKernelAcquisition() );

                    // Add some timing context on running tasks.
                    if( rThreadPool_getRunning( g_hbs_state.hThreadPool, &tasks, &nTasks ) )
                    {
                        if( NULL != ( taskList = rList_new( RP_TAGS_THREADS, RPCM_SEQUENCE ) ) )
                        {
                            for( i = 0; i < nTasks; i++ )
                            {
                                if( NULL != ( task = rSequence_new() ) )
                                {
                                    rSequence_addRU32( task, RP_TAGS_THREAD_ID, tasks[ i ].tid );
                                    rSequence_addRU32( task, RP_TAGS_HCP_FILE_ID, tasks[ i ].fileId );
                                    rSequence_addRU32( task, RP_TAGS_HCP_LINE_NUMBER, tasks[ i ].lineNum );
                                    libOs_getThreadTime( tasks[ i ].tid, &threadTime );
                                    rSequence_addTIMEDELTA( task, RP_TAGS_TIMEDELTA, threadTime );

                                    if( !rList_addSEQUENCE( taskList, task ) )
                                    {
                                        rSequence_free( task );
                                    }
                                }
                            }

                            if( !rSequence_addLIST( message, RP_TAGS_THREADS, taskList ) )
                            {
                                rList_free( taskList );
                            }
                        }

                        rpal_memory_free( tasks );
                    }

                    if( !sendSingleMessageHome( wrapper ) )
                    {
                        rpal_debug_warning( "failed to send sync" );
                    }
                }
                    
                rSequence_free( wrapper );
            }
            else
            {
                rSequence_free( wrapper );
                rSequence_free( message );
            }
        }
        else
        {
            rSequence_free( wrapper );
        }
    }

    return NULL;
}

static RBOOL
    startCollectors
    (

    )
{
    RBOOL isSuccess = FALSE;
    RU32 i = 0;

    rEvent_unset( g_hbs_state.isTimeToStop );
    if( NULL != ( g_hbs_state.hThreadPool = rThreadPool_create( 1, 
                                                                30,
                                                                MSEC_FROM_SEC( 10 ) ) ) )
    {
        isSuccess = TRUE;

        // We always schedule a boilerplate sync.
        rThreadPool_scheduleRecurring( g_hbs_state.hThreadPool, 
                                       HBS_SYNC_INTERVAL, 
                                       (rpal_thread_pool_func)issueSync, 
                                       NULL, 
                                       FALSE );

        for( i = 0; i < ARRAY_N_ELEM( g_hbs_state.collectors ); i++ )
        {
            if( g_hbs_state.collectors[ i ].isEnabled )
            {
                if( !g_hbs_state.collectors[ i ].init( &g_hbs_state, g_hbs_state.collectors[ i ].conf ) )
                {
                    isSuccess = FALSE;
                    rpal_debug_warning( "collector %d failed to init.", i );
                }
                else
                {
                    rpal_debug_info( "collector %d started.", i );
                }
            }
            else
            {
                rpal_debug_info( "collector %d disabled.", i );
            }
        }
    }

    return isSuccess;
}

static RVOID
    sendStartupEvent
    (

    )
{
    rSequence wrapper = NULL;
    rSequence startupEvent = NULL;

    if( NULL != ( wrapper = rSequence_new() ) )
    {
        if( NULL != ( startupEvent = rSequence_new() ) )
        {
            if( rSequence_addSEQUENCE( wrapper, RP_TAGS_NOTIFICATION_STARTING_UP, startupEvent ) )
            {
                hbs_timestampEvent( startupEvent, 0 );
                if( !rQueue_add( g_hbs_state.outQueue, wrapper, 0 ) )
                {
                    rSequence_free( wrapper );
                }
            }
            else
            {
                rSequence_free( wrapper );
                rSequence_free( startupEvent );
            }
        }
        else
        {
            rSequence_free( wrapper );
        }
    }
}

static RVOID
    sendShutdownEvent
    (

    )
{
    rSequence wrapper = NULL;
    rSequence shutdownEvent = NULL;

    if( NULL != ( wrapper = rSequence_new() ) )
    {
        if( NULL != ( shutdownEvent = rSequence_new() ) )
        {
            if( rSequence_addSEQUENCE( wrapper, RP_TAGS_NOTIFICATION_SHUTTING_DOWN, shutdownEvent ) )
            {
                hbs_timestampEvent( shutdownEvent, 0 );
                // There is no point queuing it up since we're exiting
                // so we'll try to send it right away.
                sendSingleMessageHome( shutdownEvent );
                rSequence_free( wrapper );
            }
            else
            {
                rSequence_free( wrapper );
                rSequence_free( shutdownEvent );
            }
        }
        else
        {
            rSequence_free( wrapper );
        }
    }
}

typedef struct
{
    RU32 eventId;
    rSequence event;
} _cloudNotifStub;

static
RPVOID
    _handleCloudNotification
    (
        rEvent isTimeToStop,
        _cloudNotifStub* pEventInfo
    )
{
    UNREFERENCED_PARAMETER( isTimeToStop );
    
    if( rpal_memory_isValid( pEventInfo ) )
    {
        if( rpal_memory_isValid( pEventInfo->event ) )
        {
            notifications_publish( pEventInfo->eventId, pEventInfo->event );
            rSequence_free( pEventInfo->event );
        }

        rpal_memory_free( pEventInfo );
    }
    
    return NULL;
}

static RVOID
    publishCloudNotifications
    (
        rList notifications
    )
{
    rSequence notif = NULL;
    RPU8 buff = NULL;
    RU32 buffSize = 0;
    RPU8 sig = NULL;
    RU32 sigSize = 0;
    rpHCPId curId = { 0 };
    rSequence cloudEvent = NULL;
    rSequence targetId = { 0 };
    RU64 expiry = 0;
    rpHCPId tmpId = { 0 };
    rSequence receipt = NULL;
    _cloudNotifStub* cloudEventStub = NULL;

    while( rList_getSEQUENCE( notifications, RP_TAGS_HBS_CLOUD_NOTIFICATION, &notif ) )
    {
        cloudEvent = NULL;

        if( NULL == cloudEventStub )
        {
            cloudEventStub = rpal_memory_alloc( sizeof( *cloudEventStub ) );
        }

        if( rSequence_getBUFFER( notif, RP_TAGS_BINARY, &buff, &buffSize ) &&
            rSequence_getBUFFER( notif, RP_TAGS_SIGNATURE, &sig, &sigSize ) )
        {
            if( CryptoLib_verify( buff, buffSize, hbs_cloud_pub_key, sig ) )
            {
                if( !rpHcpI_getId( &curId ) )
                {
                    rpal_debug_error( "error getting current id for cloud notifications." );
                }
                else
                {
                    if( !rSequence_deserialise( &cloudEvent, buff, buffSize, NULL ) )
                    {
                        cloudEvent = NULL;
                        rpal_debug_warning( "error deserializing cloud event." );
                    }
                }
            }
            else
            {
                rpal_debug_warning( "cloud event signature invalid." );
            }
        }

        if( rpal_memory_isValid( cloudEvent ) )
        {
            if( rSequence_getSEQUENCE( cloudEvent, RP_TAGS_HCP_ID, &targetId ) &&
                rSequence_getRU32( cloudEvent, RP_TAGS_HBS_NOTIFICATION_ID, &(cloudEventStub->eventId) ) &&
                rSequence_getSEQUENCE( cloudEvent, RP_TAGS_HBS_NOTIFICATION, &(cloudEventStub->event) ) )
            {
                rSequence_getTIMESTAMP( cloudEvent, RP_TAGS_EXPIRY, &expiry );
                hbs_timestampEvent( cloudEvent, 0 );

                tmpId = rpHcpI_seqToHcpId( targetId );

                curId.id.configId = 0;
                tmpId.id.configId = 0;
                
                if( NULL != ( receipt = rSequence_new() ) )
                {
                    if( rSequence_addSEQUENCE( receipt, 
                                               RP_TAGS_HBS_CLOUD_NOTIFICATION, 
                                               rSequence_duplicate( cloudEvent ) ) )
                    {
                        if( !rQueue_add( g_hbs_state.outQueue, receipt, 0 ) )
                        {
                            rSequence_free( receipt );
                            receipt = NULL;
                        }
                    }
                    else
                    {
                        rSequence_free( receipt );
                        receipt = NULL;
                    }
                }

                if( curId.raw == tmpId.raw &&
                    rpal_time_getGlobal() <= expiry )
                {
                    if( NULL != ( cloudEventStub->event = rSequence_duplicate( cloudEventStub->event ) ) )
                    {
                        if( rThreadPool_task( g_hbs_state.hThreadPool, 
                                              (rpal_thread_pool_func)_handleCloudNotification,
                                              cloudEventStub ) )
                        {
                            // The handler will free this stub
                            cloudEventStub = NULL;
                            rpal_debug_info( "new cloud event published." );
                        }
                        else
                        {
                            rSequence_free( cloudEventStub->event );
                            cloudEventStub->event = NULL;
                            rpal_debug_error( "error publishing event from cloud." );
                        }
                    }
                }
                else
                {
                    rpal_debug_warning( "event expired or for wrong id." );
                }
            }

            if( rpal_memory_isValid( cloudEvent ) )
            {
                rSequence_free( cloudEvent );
                cloudEvent = NULL;
            }
        }
    }

    if( NULL != cloudEventStub )
    {
        rpal_memory_free( cloudEventStub );
        cloudEventStub = NULL;
    }
}

//=============================================================================
//  Entry Points
//=============================================================================
RVOID
    RpHcpI_receiveMessage
    (
        rSequence message
    )
{
    rSequence sync = NULL;
    RU8* profileHash = NULL;
    RU32 hashSize = 0;
    rList configurations = NULL;
    rList cloudNotifications = NULL;

    // If it's an internal HBS message we'll process it right away.
    if( rSequence_getSEQUENCE( message, RP_TAGS_NOTIFICATION_SYNC, &sync ) )
    {
        rpal_debug_info( "receiving hbs sync" );
        if( rSequence_getBUFFER( sync, RP_TAGS_HASH, &profileHash, &hashSize ) &&
            CRYPTOLIB_HASH_SIZE == hashSize &&
            rSequence_getLIST( sync, RP_TAGS_HBS_CONFIGURATIONS, &configurations ) )
        {
            if( NULL != ( configurations = rList_duplicate( configurations ) ) )
            {
                if( rMutex_lock( g_hbs_state.mutex ) )
                {
                    rpal_debug_info( "sync has new profile, restarting collectors" );
                    rpal_memory_memcpy( g_hbs_state.currentConfigHash, profileHash, hashSize );

                    // We're going to shut down all collectors, swap the configs and restart them.
                    shutdownCollectors();
                    updateCollectorConfigs( configurations );
                    startCollectors();

                    // Check to see if this has changed the kernel acquisition status.
                    checkKernelAcquisition();

                    rMutex_unlock( g_hbs_state.mutex );
                }

                rList_free( configurations );
            }
        }
        else
        {
            rpal_debug_warning( "hbs sync missing critical component" );
        }
    }
    else if( rSequence_getLIST( message, RP_TAGS_HBS_CLOUD_NOTIFICATIONS, &cloudNotifications ) )
    {
        // If it's a list of notifications we'll pass them on to be verified.
        rpal_debug_info( "received %d cloud notifications", rList_getNumElements( cloudNotifications ) );
        publishCloudNotifications( cloudNotifications );
    }
    else
    {
        rpal_debug_warning( "unknown message received" );
    }
}

RU32
RPAL_THREAD_FUNC
    RpHcpI_mainThread
    (
        rEvent isTimeToStop
    )
{
    RU32 ret = 0;

    rSequence staticConfig = NULL;
    rList tmpConfigurations = NULL;
    RU8* tmpBuffer = NULL;
    RU32 tmpSize = 0;
    rList exfilList = NULL;
    rSequence exfilMessage = NULL;
    rEvent newExfilEvents = NULL;

    FORCE_LINK_THAT( HCP_IFACE );

    CryptoLib_init();
    atoms_init();

    if( !getPrivileges() )
    {
        rpal_debug_info( "special privileges not acquired" );
    }

    // This is the event for the collectors, it is different than the
    // hbs proper event so that we can restart the collectors without
    // signaling hbs as a whole.
    if( NULL == ( g_hbs_state.isTimeToStop = rEvent_create( TRUE ) ) )
    {
        return (RU32)-1;
    }

    if( NULL == ( g_hbs_state.mutex = rMutex_create() ) )
    {
        rEvent_free( g_hbs_state.isTimeToStop );
        return (RU32)-1;
    }

    // Initial boot and we have no profile yet, we'll load a dummy
    // blank profile and use our defaults.
    if( NULL != ( tmpConfigurations = rList_new( RP_TAGS_HCP_MODULES, RPCM_SEQUENCE ) ) )
    {
        updateCollectorConfigs( tmpConfigurations );
        rpal_debug_info( "setting empty profile" );
        rList_free( tmpConfigurations );
    }

    // By default, no collectors are running
    rEvent_set( g_hbs_state.isTimeToStop );

    // We attempt to load some initial config from the serialized
    // rSequence that can be patched in this binary.
    if( NULL != ( staticConfig = getStaticConfig() ) )
    {
        if( rSequence_getBUFFER( staticConfig, RP_TAGS_HBS_ROOT_PUBLIC_KEY, &tmpBuffer, &tmpSize ) )
        {
            hbs_cloud_pub_key = rpal_memory_duplicate( tmpBuffer, tmpSize );
            if( NULL == hbs_cloud_pub_key )
            {
                hbs_cloud_pub_key = hbs_cloud_default_pub_key;
            }
            rpal_debug_info( "loading hbs root public key from static config" );
        }

        if( rSequence_getRU32( staticConfig, RP_TAGS_MAX_QUEUE_SIZE, &g_hbs_state.maxQueueNum ) )
        {
            rpal_debug_info( "loading max queue size from static config" );
        }
        else
        {
            g_hbs_state.maxQueueNum = HBS_EXFIL_QUEUE_MAX_NUM;
        }

        if( rSequence_getRU32( staticConfig, RP_TAGS_MAX_SIZE, &g_hbs_state.maxQueueSize ) )
        {
            rpal_debug_info( "loading max queue num from static config" );
        }
        else
        {
            g_hbs_state.maxQueueSize = HBS_EXFIL_QUEUE_MAX_SIZE;
        }

        rSequence_free( staticConfig );
    }
    else
    {
        hbs_cloud_pub_key = hbs_cloud_default_pub_key;
        g_hbs_state.maxQueueNum = HBS_EXFIL_QUEUE_MAX_NUM;
        g_hbs_state.maxQueueSize = HBS_EXFIL_QUEUE_MAX_SIZE;
    }

    if( !rQueue_create( &g_hbs_state.outQueue, freeExfilEvent, g_hbs_state.maxQueueNum ) )
    {
        rEvent_free( g_hbs_state.isTimeToStop );
        return (RU32)-1;
    }

    newExfilEvents = rQueue_getNewElemEvent( g_hbs_state.outQueue );

    g_hbs_state.isOnlineEvent = rpHcpI_getOnlineEvent();

    // We simply enqueue a message to let the cloud know we're starting
    sendStartupEvent();

    if( !rEvent_wait( isTimeToStop, 0 ) )
    {
        startCollectors();
    }

    // We'll wait for the very first online notification to start syncing.
    while( !rEvent_wait( isTimeToStop, 0 ) )
    {
        if( rEvent_wait( g_hbs_state.isOnlineEvent, MSEC_FROM_SEC( 5 ) ) )
        {
            // From the first sync, we'll schedule recurring ones.
            issueSync( g_hbs_state.isTimeToStop, NULL );
            break;
        }
    }

    // We've connected to the cloud at least once, did a sync once, let's start normal exfil.
    while( !rEvent_wait( isTimeToStop, 0 ) )
    {
        if( rEvent_wait(g_hbs_state.isOnlineEvent, MSEC_FROM_SEC( 1 ) ) &&
            rEvent_wait( newExfilEvents, MSEC_FROM_SEC( 1 ) ) )
        {
            if( NULL != ( exfilList = rList_new( RP_TAGS_MESSAGE, RPCM_SEQUENCE ) ) )
            {
                while( rQueue_remove( g_hbs_state.outQueue, &exfilMessage, NULL, 0 ) )
                {
                    if( !rList_addSEQUENCE( exfilList, exfilMessage ) )
                    {
                        rpal_debug_error( "dropping exfil message" );
                        rSequence_free( exfilMessage );
                    }

                    if( HBS_MAX_OUBOUND_FRAME_SIZE <= rList_getNumElements( exfilList ) )
                    {
                        break;
                    }
                }

                if( rpHcpI_sendHome( exfilList ) )
                {
                    rList_free( exfilList );
                }
                else
                {
                    // Failed to send the data home, so we'll re-queue it.
                    if( g_hbs_state.maxQueueNum < rList_getNumElements( exfilList ) ||
                        g_hbs_state.maxQueueSize < rList_getEstimateSize( exfilList ) )
                    {
                        // We have an overflow of the queues, dropping will occur.
                        rpal_debug_warning( "queue thresholds reached, dropping %d messages", 
                                            rList_getNumElements( exfilList ) );
                        rList_free( exfilList );
                    }
                    else
                    {
                        rpal_debug_info( "transmition failed, re-adding %d messages.", rList_getNumElements( exfilList ) );

                        // We will attempt to re-add the existing messages back in the queue since this failed
                        rList_resetIterator( exfilList );
                        while( rList_getSEQUENCE( exfilList, RP_TAGS_MESSAGE, &exfilMessage ) )
                        {
                            if( !rQueue_add( g_hbs_state.outQueue, exfilMessage, 0 ) )
                            {
                                rSequence_free( exfilMessage );
                            }
                        }
                        rList_shallowFree( exfilList );
                    }
                }
            }
        }
    }

    // We issue one last beacon indicating we are stopping
    sendShutdownEvent();

    // Shutdown everything
    shutdownCollectors();

    // Cleanup the last few resources
    rEvent_free( g_hbs_state.isTimeToStop );
    rQueue_free( g_hbs_state.outQueue );

    rMutex_free( g_hbs_state.mutex );

    CryptoLib_deinit();

    if( hbs_cloud_default_pub_key != hbs_cloud_pub_key &&
        NULL != hbs_cloud_pub_key )
    {
        rpal_memory_free( hbs_cloud_pub_key );
        hbs_cloud_pub_key = NULL;
    }

    if( kAcq_isAvailable() )
    {
        kAcq_deinit();
    }
    
    atoms_deinit();

    return ret;
}

