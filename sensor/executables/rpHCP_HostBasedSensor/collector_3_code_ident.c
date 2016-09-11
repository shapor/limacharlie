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
#include <librpcm/librpcm.h>
#include "collectors.h"
#include <notificationsLib/notificationsLib.h>
#include <rpHostCommonPlatformLib/rTags.h>
#include <cryptoLib/cryptoLib.h>
#include <libOs/libOs.h>

#define RPAL_FILE_ID 72

#define _MAX_FILE_HASH_SIZE                 (1024 * 1024 * 20)

static rBloom g_knownCode = NULL;
static rMutex g_mutex = NULL;


static
RVOID
    processCodeIdent
    (
        RNATIVESTR name,
        CryptoLib_Hash* pFileHash,
        RU64 codeSize,
        rSequence originalEvent
    )
{
    struct
    {
        CryptoLib_Hash fileHash;
        RU64 codeSize;
        RNATIVECHAR fileName[ RPAL_MAX_PATH ];
    } ident = { 0 };

    rSequence notif = NULL;
    rSequence sig = NULL;
    RBOOL isSigned = FALSE;
    RBOOL isVerifiedLocal = FALSE;
    RBOOL isVerifiedGlobal = FALSE;
    RPU8 pAtomId = NULL;
    RU32 atomSize = 0;
    
    ident.codeSize = codeSize;

    if( NULL != name )
    {
        rpal_memory_memcpy( &ident.fileName, 
                            name, 
                            MIN_OF( sizeof( ident.fileName ), 
                                    rpal_string_strsize( name ) ) );
    }

    if( NULL != pFileHash )
    {
        rpal_memory_memcpy( &ident.fileHash, pFileHash, sizeof( *pFileHash ) );
    }

    if( rMutex_lock( g_mutex ) )
    {
        if( rpal_bloom_addIfNew( g_knownCode, &ident, sizeof( ident ) ) )
        {
            rMutex_unlock( g_mutex );

            if( NULL != ( notif = rSequence_new() ) )
            {
                hbs_markAsRelated( originalEvent, notif );

                if( ( rSequence_addSTRINGN( notif, RP_TAGS_FILE_PATH, name ) ||
                      rSequence_addSTRINGN( notif, RP_TAGS_DLL, name ) ||
                      rSequence_addSTRINGN( notif, RP_TAGS_EXECUTABLE, name ) ) &&
                    rSequence_addRU32( notif, RP_TAGS_MEMORY_SIZE, (RU32)codeSize ) &&
                    hbs_timestampEvent( notif, 0 ) )
                {
                    if( rSequence_getBUFFER( originalEvent, RP_TAGS_HBS_THIS_ATOM, &pAtomId, &atomSize ) )
                    {
                        rSequence_removeElement( notif, RP_TAGS_HBS_PARENT_ATOM, RPCM_BUFFER );
                        rSequence_addBUFFER( notif, RP_TAGS_HBS_PARENT_ATOM, pAtomId, atomSize );
                        rSequence_removeElement( notif, RP_TAGS_HBS_THIS_ATOM, RPCM_BUFFER );
                    }

                    if( NULL != pFileHash )
                    {
                        rSequence_addBUFFER( notif, RP_TAGS_HASH, (RPU8)pFileHash, sizeof( *pFileHash ) );
                    }

                    if( libOs_getSignature( name,
                                            &sig,
                                            ( OSLIB_SIGNCHECK_NO_NETWORK | OSLIB_SIGNCHECK_CHAIN_VERIFICATION ),
                                            &isSigned,
                                            &isVerifiedLocal,
                                            &isVerifiedGlobal ) )
                    {
                        if( !rSequence_addSEQUENCE( notif, RP_TAGS_SIGNATURE, sig ) )
                        {
                            rSequence_free( sig );
                        }
                    }

                    hbs_publish( RP_TAGS_NOTIFICATION_CODE_IDENTITY, notif );
                }
                rSequence_free( notif );
            }
        }
        else
        {
            rMutex_unlock( g_mutex );
        }
    }
}

static
RVOID
    processNewProcesses
    (
        rpcm_tag notifType,
        rSequence event
    )
{
    RNATIVESTR nameN = NULL;
    CryptoLib_Hash fileHash = { 0 };
    RU64 size = 0;

    UNREFERENCED_PARAMETER( notifType );

    if( rpal_memory_isValid( event ) )
    {
        if( rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN ) )
        {
            if( _MAX_FILE_HASH_SIZE < rpal_file_getSize( nameN, TRUE ) )
            {
                // We already read from the event, but we will be careful.
                rSequence_unTaintRead( event );
                rSequence_addRU32( event, RP_TAGS_ERROR, RPAL_ERROR_FILE_TOO_LARGE );

                // We need to re-get the paths in case adding the error triggered
                // a change in the structure.
                rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN );
            }
            else
            {
                if( !CryptoLib_hashFile( nameN, &fileHash, TRUE ) )
                {
                    rpal_debug_info( "unable to fetch file hash for ident" );
                }
            }
            
            rSequence_getRU64( event, RP_TAGS_MEMORY_SIZE, &size );

            processCodeIdent( nameN, &fileHash, size, event );
        }
    }
}


static
RVOID
    processNewModule
    (
        rpcm_tag notifType,
        rSequence event
    )
{
    RNATIVESTR nameN = NULL;
    CryptoLib_Hash fileHash = { 0 };
    RU64 size = 0;

    UNREFERENCED_PARAMETER( notifType );

    if( rpal_memory_isValid( event ) )
    {
        if( rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN ) )
        {
            if( _MAX_FILE_HASH_SIZE < rpal_file_getSize( nameN, TRUE ) )
            {
                // We already read from the event, but we will be careful.
                rSequence_unTaintRead( event );
                rSequence_addRU32( event, RP_TAGS_ERROR, RPAL_ERROR_FILE_TOO_LARGE );

                // We need to re-get the paths in case adding the error triggered
                // a change in the structure.
                rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN );
            }
            else
            {
                if( !CryptoLib_hashFile( nameN, &fileHash, TRUE ) )
                {
                    rpal_debug_info( "unable to fetch file hash for ident" );
                }
            }

            rSequence_getRU64( event, RP_TAGS_MEMORY_SIZE, &size );

            processCodeIdent( nameN, &fileHash, size, event );
        }
    }
}


static
RVOID
    processHashedEvent
    (
        rpcm_tag notifType,
        rSequence event
    )
{
    RNATIVESTR nameN = NULL;
    CryptoLib_Hash* pHash = NULL;
    CryptoLib_Hash localHash = { 0 };
    
    UNREFERENCED_PARAMETER( notifType );

    if( rpal_memory_isValid( event ) )
    {
        if( rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN ) ||
            rSequence_getSTRINGN( event, RP_TAGS_DLL, &nameN ) ||
            rSequence_getSTRINGN( event, RP_TAGS_EXECUTABLE, &nameN ) )
        {
            rSequence_getBUFFER( event, RP_TAGS_HASH, (RPU8*)&pHash, NULL );
            
            if( NULL == pHash )
            {
                if( _MAX_FILE_HASH_SIZE < rpal_file_getSize( nameN, TRUE ) )
                {
                    rSequence_unTaintRead( event );
                    rSequence_addRU32( event, RP_TAGS_ERROR, RPAL_ERROR_FILE_TOO_LARGE );

                    if( rSequence_getSTRINGN( event, RP_TAGS_FILE_PATH, &nameN ) ||
                        rSequence_getSTRINGN( event, RP_TAGS_DLL, &nameN ) ||
                        rSequence_getSTRINGN( event, RP_TAGS_EXECUTABLE, &nameN ) )
                    {
                        // Find the name again with shortcircuit
                    }
                }
                else if( CryptoLib_hashFile( nameN, &localHash, TRUE ) )
                {
                    pHash = &localHash;
                }
            }

            processCodeIdent( nameN, pHash, 0, event );
        }
    }
}

static
RVOID
    processGenericSnapshot
    (
        rpcm_tag notifType,
        rSequence event
    )
{
    rList entityList = NULL;
    rSequence entity = NULL;

    UNREFERENCED_PARAMETER( notifType );

    if( rpal_memory_isValid( event ) )
    {
        if( rSequence_getLIST( event, RP_TAGS_AUTORUNS, &entityList ) ||
            rSequence_getLIST( event, RP_TAGS_SVCS, &entityList ) ||
            rSequence_getLIST( event, RP_TAGS_PROCESSES, &entityList ) )
        {
            // Go through the elements, whatever tag
            while( rList_getSEQUENCE( entityList, RPCM_INVALID_TAG, &entity ) )
            {
                processHashedEvent( notifType, entity );
            }
        }
    }
}

//=============================================================================
// COLLECTOR INTERFACE
//=============================================================================

rpcm_tag collector_3_events[] = { RP_TAGS_NOTIFICATION_CODE_IDENTITY,
                                  0 };

RBOOL
    collector_3_init
    (
        HbsState* hbsState,
        rSequence config
    )
{
    RBOOL isSuccess = FALSE;
    UNREFERENCED_PARAMETER( config );

    if( NULL != hbsState )
    {
        if( NULL != ( g_mutex = rMutex_create() ) )
        {
            if( NULL != ( g_knownCode = rpal_bloom_create( 50000, 0.00001 ) ) )
            {
                isSuccess = FALSE;

                if( notifications_subscribe( RP_TAGS_NOTIFICATION_NEW_PROCESS, NULL, 0, NULL, processNewProcesses ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_MODULE_LOAD, NULL, 0, NULL, processNewModule ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_SERVICE_CHANGE, NULL, 0, NULL, processHashedEvent ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_DRIVER_CHANGE, NULL, 0, NULL, processHashedEvent ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_AUTORUN_CHANGE, NULL, 0, NULL, processHashedEvent ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_OS_SERVICES_REP, NULL, 0, NULL, processGenericSnapshot ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_OS_DRIVERS_REP, NULL, 0, NULL, processGenericSnapshot ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_OS_PROCESSES_REP, NULL, 0, NULL, processGenericSnapshot ) &&
                    notifications_subscribe( RP_TAGS_NOTIFICATION_OS_AUTORUNS_REP, NULL, 0, NULL, processGenericSnapshot ) )
                {
                    isSuccess = TRUE;
                }
                else
                {
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_NEW_PROCESS, NULL, processNewProcesses );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_MODULE_LOAD, NULL, processNewModule );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_SERVICE_CHANGE, NULL, processHashedEvent );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_DRIVER_CHANGE, NULL, processHashedEvent );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_AUTORUN_CHANGE, NULL, processHashedEvent );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_SERVICES_REP, NULL, processGenericSnapshot );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_DRIVERS_REP, NULL, processGenericSnapshot );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_PROCESSES_REP, NULL, processGenericSnapshot );
                    notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_AUTORUNS_REP, NULL, processGenericSnapshot );
                    rpal_bloom_destroy( g_knownCode );
                    rMutex_free( g_mutex );
                    g_mutex = NULL;
                }
            }
            else
            {
                rMutex_free( g_mutex );
                g_mutex = NULL;
            }
        }
    }

    return isSuccess;
}

RBOOL
    collector_3_cleanup
    (
        HbsState* hbsState,
        rSequence config
    )
{
    RBOOL isSuccess = FALSE;

    UNREFERENCED_PARAMETER( config );

    if( NULL != hbsState )
    {
        if( notifications_unsubscribe( RP_TAGS_NOTIFICATION_NEW_PROCESS, NULL, processNewProcesses ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_MODULE_LOAD, NULL, processNewModule ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_SERVICE_CHANGE, NULL, processHashedEvent ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_DRIVER_CHANGE, NULL, processHashedEvent ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_AUTORUN_CHANGE, NULL, processHashedEvent ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_SERVICES_REP, NULL, processGenericSnapshot ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_DRIVERS_REP, NULL, processGenericSnapshot ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_PROCESSES_REP, NULL, processGenericSnapshot ) &&
            notifications_unsubscribe( RP_TAGS_NOTIFICATION_OS_AUTORUNS_REP, NULL, processGenericSnapshot ) )
        {
            isSuccess = TRUE;
        }

        rpal_bloom_destroy( g_knownCode );
        g_knownCode = NULL;

        rMutex_free( g_mutex );
        g_mutex = NULL;
    }

    return isSuccess;
}
