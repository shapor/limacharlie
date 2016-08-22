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

#ifndef _KERNEL_ACQUISITION_LIB_COMMON_H
#define _KERNEL_ACQUISITION_LIB_COMMON_H

#include <rpal/rpal_datatypes.h>

#ifdef RPAL_PLATFORM_MACOSX
    #define ACQUISITION_COMMS_NAME          "com.refractionpoint.hbs.acq"
#elif defined( RPAL_PLATFORM_WINDOWS )
    
    #define ACQUISITION_COMMS_NAME          _WCH("rp_hcp_hbs_acq")
    #define DEVICE_ID                       44223
    #define DEVICE_FUNCTION_CODE            0x400
    #define IOCTL_EXCHANGE_DATA             CTL_CODE( DEVICE_ID, \
                                                      DEVICE_FUNCTION_CODE, \
                                                      METHOD_BUFFERED, \
                                                      FILE_READ_ACCESS )
#endif

#define ACQUISITION_COMMS_CHALLENGE         0xDEADBEEF
#define ACQUISITION_COMMS_RESPONSE          0x010A020B


#define KERNEL_ACQ_OP_PING                  0
#define KERNEL_ACQ_OP_GET_NEW_PROCESSES     1
#define KERNEL_ACQ_OP_GET_NEW_FILE_IO       2
#define KERNEL_ACQ_OP_MODULE_LOAD           3
#define KERNEL_ACQ_OP_COUNT                 4

#pragma warning( disable: 4200 ) // Disabling error on zero-sized arrays

typedef struct
{
#ifdef RPAL_PLATFORM_MACOSX
    RPU8 pArgs;             // Arguments
    RU32 argsSize;          // Size of Arguments
    RPU8 pResult;           // Result of op
    RU32 resultSize;        // Size of results
    RU32* pSizeUsed;        // Size in results used
#elif defined( RPAL_PLATFORM_WINDOWS )
    RU32 op;
    RU32 dataOffset;
    RU32 argsSize;
    RU8 data[];
#else
    RU32 unused;
#endif
} KernelAcqCommand;


//==============================================================================
//  Collector Specific Data Structures
//==============================================================================

#define KERNEL_ACQ_NO_USER_ID               ((RU32)(-1))
typedef struct
{
    RU32 pid;
    RU32 ppid;
    RU32 uid;
    RU64 ts;
    RNATIVECHAR path[ 513 ];
    RNATIVECHAR cmdline[ 513 ];

} KernelAcqProcess;

#define KERNEL_ACQ_FILE_ACTION_ADDED        1
#define KERNEL_ACQ_FILE_ACTION_REMOVED      2
#define KERNEL_ACQ_FILE_ACTION_MODIFIED     3
#define KERNEL_ACQ_FILE_ACTION_RENAME_OLD   4
#define KERNEL_ACQ_FILE_ACTION_RENAME_NEW   5
typedef struct
{
    RU32 action;
    RU32 pid;
    RU32 uid;
    RU64 ts;
    RNATIVECHAR path[ 513 ];

} KernelAcqFileIo;

typedef struct
{
    RU32 pid;
    RPVOID baseAddress;
    RU64 imageSize;
    RU64 ts;
    RNATIVECHAR path[ 513 ];
} KernelAcqModule;

#endif