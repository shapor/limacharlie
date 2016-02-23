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

#define RPAL_FILE_ID          100

#define _EVENT_BUFFER_SIZE      (10 * 1024)
static RPU8 g_event_buffer = NULL;

static
RPVOID
    psEventLogger
    (
        rEvent isTimeToStop,
        RPVOID ctx
    )
{
    UNREFERENCED_PARAMETER( ctx );

#ifdef RPAL_PLATFORM_WINDOWS
    HANDLE hEventLog = NULL;
    RWCHAR logName[] = _WCH( "Windows PowerShell" );

    if( NULL == ( hEventLog = OpenEventLogW( NULL, logName ) ) )
    {
        rpal_debug_warning( "could not open event log" );
        return NULL;
    }

    if( NULL == ( g_event_buffer = rpal_memory_alloc( _EVENT_BUFFER_SIZE ) ) )
    {
        return NULL;
    }

    while( !rEvent_wait( isTimeToStop, MSEC_FROM_SEC( 5 ) ) )
    {
        while( !rEvent_wait( isTimeToStop, 0 ) &&
            ReadEventLogW( hEventLog, EVENTLOG_SEQUENTIAL_READ, 0,  ) )
        {

        }
    }

    CloseEventLog( hEventLog );
    rpal_memory_free( g_event_buffer );

#else
    UNREFERENCED_PARAMETER( isTimeToStop );
#endif

    return NULL;
}

//=============================================================================
// COLLECTOR INTERFACE
//=============================================================================

rpcm_tag collector_2_events[] = { RP_TAGS_NOTIFICATION_POWERSHELL_CMD,
                                  0 };

RBOOL
collector_17_init
    (
        HbsState* hbsState,
        rSequence config
    )
{
    RBOOL isSuccess = FALSE;
    UNREFERENCED_PARAMETER( config );

    if( NULL != hbsState )
    {
        if( isSuccess )
        {
            isSuccess = FALSE;

            if( rThreadPool_task( hbsState->hThreadPool, psEventLogger, NULL ) )
            {
                isSuccess = TRUE;
            }
        }
    }

    return isSuccess;
}

RBOOL
collector_17_cleanup
    (
        HbsState* hbsState,
        rSequence config
    )
{
    RBOOL isSuccess = FALSE;

    UNREFERENCED_PARAMETER( config );

    if( NULL != hbsState )
    {

        isSuccess = TRUE;
    }

    return isSuccess;
}
