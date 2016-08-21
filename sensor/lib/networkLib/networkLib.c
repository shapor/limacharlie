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

#include <networkLib/networkLib.h>

#define RPAL_FILE_ID    41

#ifdef RPAL_PLATFORM_WINDOWS
#include <iphlpapi.h>
#include <windows_undocumented.h>
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <netdb.h>
#include <unistd.h>
#endif

#pragma warning( disable: 4127 ) // Disabling error on constant expression in condition

#ifndef SOCKET_ERROR
#define SOCKET_ERROR (-1)
#endif

NetLib_Tcp4Table*
    NetLib_getTcp4Table
    (

    )
{
    NetLib_Tcp4Table* table = NULL;
#ifdef RPAL_PLATFORM_WINDOWS
    PMIB_TCPTABLE winTable = NULL;
    RU32 size = 0;
    RU32 error = 0;
    RBOOL isFinished = FALSE;
    RU32 i = 0;

    while( !isFinished )
    {
        if( NULL != GetExtendedTcpTable )
        {
            error = GetExtendedTcpTable( winTable, (DWORD*)&size, FALSE, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0 );
        }
        else
        {
            error = GetTcpTable( winTable, (PDWORD)&size, FALSE );
        }

        if( ERROR_INSUFFICIENT_BUFFER == error &&
            0 != size )
        {
            if( NULL == ( winTable = rpal_memory_realloc( winTable, size ) ) )
            {
                isFinished = TRUE;
            }
        }
        else if( ERROR_SUCCESS != error )
        {
            rpal_memory_free( winTable );
            winTable = NULL;
            isFinished = TRUE;
        }
        else
        {
            isFinished = TRUE;
        }
    }

    if( NULL != winTable )
    {
        if( NULL != ( table = rpal_memory_alloc( sizeof( NetLib_Tcp4Table ) + 
                                                    ( winTable->dwNumEntries * sizeof( NetLib_Tcp4TableRow ) ) ) ) )
        {
            table->nRows = winTable->dwNumEntries;

            for( i = 0; i < winTable->dwNumEntries; i++ )
            {
                if( NULL == GetExtendedTcpTable )
                {
                    table->rows[ i ].destIp = winTable->table[ i ].dwRemoteAddr;
                    table->rows[ i ].destPort = (RU16)winTable->table[ i ].dwRemotePort;
                    table->rows[ i ].sourceIp = winTable->table[ i ].dwLocalAddr;
                    table->rows[ i ].sourcePort = (RU16)winTable->table[ i ].dwLocalPort;
                    table->rows[ i ].state = winTable->table[ i ].dwState;
                    table->rows[ i ].pid = 0;
                }
                else
                {
                    table->rows[ i ].destIp = ((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwRemoteAddr;
                    table->rows[ i ].destPort = (RU16)((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwRemotePort;
                    table->rows[ i ].sourceIp = ((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwLocalAddr;
                    table->rows[ i ].sourcePort = (RU16)((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwLocalPort;
                    table->rows[ i ].state = ((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwState;
                    table->rows[ i ].pid = ((PMIB_TCPROW_OWNER_PID)winTable->table)[ i ].dwOwningPid;
                }
            }
        }

        rpal_memory_free( winTable );
    }
#else
    rpal_debug_not_implemented();
#endif
    return table;
}

NetLib_UdpTable*
    NetLib_getUdpTable
    (

    )
{
    NetLib_UdpTable* table = NULL;
#ifdef RPAL_PLATFORM_WINDOWS
    PMIB_UDPTABLE winTable = NULL;
    RU32 size = 0;
    RU32 error = 0;
    RBOOL isFinished = FALSE;
    RU32 i = 0;

    while( !isFinished )
    {
        if( NULL != GetExtendedUdpTable )
        {
            error = GetExtendedUdpTable( winTable, (DWORD*)&size, FALSE, AF_INET, UDP_TABLE_OWNER_PID, 0 );
        }
        else
        {
            error = GetUdpTable( winTable, (PDWORD)&size, FALSE );
        }

        if( ERROR_INSUFFICIENT_BUFFER == error &&
            0 != size )
        {
            if( NULL == ( winTable = rpal_memory_realloc( winTable, size ) ) )
            {
                isFinished = TRUE;
            }
        }
        else if( ERROR_SUCCESS != error )
        {
            rpal_memory_free( winTable );
            winTable = NULL;
            isFinished = TRUE;
        }
        else
        {
            isFinished = TRUE;
        }
    }

    if( NULL != winTable )
    {
        if( NULL != ( table = rpal_memory_alloc( sizeof( NetLib_UdpTable ) + 
                                                    ( winTable->dwNumEntries * sizeof( NetLib_UdpTableRow ) ) ) ) )
        {
            table->nRows = winTable->dwNumEntries;

            for( i = 0; i < winTable->dwNumEntries; i++ )
            {
                if( NULL == GetExtendedUdpTable )
                {
                    table->rows[ i ].localIp = winTable->table[ i ].dwLocalAddr;
                    table->rows[ i ].localPort = (RU16)winTable->table[ i ].dwLocalPort;
                    table->rows[ i ].pid = 0;
                }
                else
                {
                    table->rows[ i ].localIp = ((PMIB_UDPROW_OWNER_PID)winTable->table)[ i ].dwLocalAddr;
                    table->rows[ i ].localPort = (RU16)((PMIB_UDPROW_OWNER_PID)winTable->table)[ i ].dwLocalPort;
                    table->rows[ i ].pid = ((PMIB_UDPROW_OWNER_PID)winTable->table)[ i ].dwOwningPid;
                }
            }
        }

        rpal_memory_free( winTable );
    }
#else
    rpal_debug_not_implemented();
#endif
    return table;
}


NetLibTcpConnection
    NetLib_TcpConnect
    (
        RPCHAR dest,
        RU16 port
    )
{
    NetLibTcpConnection conn = 0;

    if( NULL != dest )
    {
        RBOOL isConnected = FALSE;
        struct sockaddr_in server = { 0 };
        struct hostent* remoteHost = NULL;
        conn = socket( AF_INET, SOCK_STREAM, IPPROTO_TCP );

#ifdef RPAL_PLATFORM_WINDOWS
        if( INVALID_SOCKET == conn && WSANOTINITIALISED == WSAGetLastError() )
        {
            WSADATA wsadata = { 0 };
            if( 0 != WSAStartup( MAKEWORD( 2, 2 ), &wsadata ) )
            {
                return 0;
            }
            conn = socket( AF_INET, SOCK_STREAM, IPPROTO_TCP );
        }
#endif

        if( conn )
        {
            if( NULL != ( remoteHost = gethostbyname( dest ) ) )
            {
                rpal_memory_memcpy( &server.sin_addr, remoteHost->h_addr_list[ 0 ], remoteHost->h_length );
                server.sin_family = AF_INET;
                server.sin_port = htons( port );

                if( 0 == connect( conn, (struct sockaddr*)&server, sizeof( server ) ) )
                {
                    isConnected = TRUE;
                }
            }
        }

        if( !isConnected && 0 != conn )
        {
#ifdef RPAL_PLATFORM_WINDOWS
            closesocket( conn );
#else
            close( conn );
#endif
            conn = 0;
        }
    }

    return conn;
}

RBOOL
    NetLib_TcpDisconnect
    (
        NetLibTcpConnection conn
    )
{
    RBOOL isDisconnected = FALSE;

    if( 0 != conn )
    {
#ifdef RPAL_PLATFORM_WINDOWS
        closesocket( conn );
#else
        close( conn );
#endif
    }

    return isDisconnected;
}

RBOOL
    NetLib_TcpSend
    (
        NetLibTcpConnection conn,
        RPVOID buffer,
        RU32 bufferSize,
        rEvent stopEvent
    )
{
    RBOOL isSent = FALSE;
    RU32 nSent = 0;
    RU32 ret = 0;
    fd_set sockets;
    struct timeval timeout = { 1, 0 };
    int waitVal = 0;
    int n = 0;

    if( 0 != conn &&
        NULL != buffer &&
        0 != bufferSize )
    {
        isSent = TRUE;

        while( nSent < bufferSize && !rEvent_wait( stopEvent, 0 ) )
        {
            FD_ZERO( &sockets );
            FD_SET( conn, &sockets );
            n = (int)conn + 1;

            waitVal = select( n, NULL, &sockets, NULL, &timeout );

            if( 0 == waitVal )
            {
                continue;
            }

            if( SOCKET_ERROR == waitVal ||
                SOCKET_ERROR == ( ret = send( conn, (const char*)( (RPU8)buffer ) + nSent, bufferSize - nSent, 0 ) ) )
            {
                isSent = FALSE;
                break;
            }

            nSent += ret;
        }

        if( nSent != bufferSize )
        {
            isSent = FALSE;
        }
    }

    return isSent;
}

RBOOL
    NetLib_TcpReceive
    (
        NetLibTcpConnection conn,
        RPVOID buffer,
        RU32 bufferSize,
        rEvent stopEvent,
        RU32 timeoutSec
    )
{
    RBOOL isReceived = FALSE;
    RU32 nReceived = 0;
    RU32 ret = 0;
    fd_set sockets;
    struct timeval timeout = { 1, 0 };
    int waitVal = 0;
    RTIME expire = 0;
    int n = 0;

    if( 0 != conn &&
        NULL != buffer &&
        0 != bufferSize )
    {
        isReceived = TRUE;

        if( 0 != timeoutSec )
        {
            expire = rpal_time_getLocal() + timeoutSec;
        }

        while( nReceived < bufferSize && 
               !rEvent_wait( stopEvent, 0 ) && 
               ( 0 == timeoutSec || rpal_time_getLocal() <= expire ) )
        {
            FD_ZERO( &sockets );
            FD_SET( conn, &sockets );
            n = (int)conn + 1;

            waitVal = select( n, &sockets, NULL, NULL, &timeout );

            if( 0 == waitVal )
            {
                FD_ZERO( &sockets );
                FD_SET( conn, &sockets );
                continue;
            }

            if( SOCKET_ERROR == waitVal ||
                SOCKET_ERROR == ( ret = recv( conn, (char*)( (RPU8)buffer ) + nReceived, bufferSize - nReceived, 0 ) ) ||
                0 == ret )
            {
                isReceived = FALSE;
                break;
            }

            nReceived += ret;
        }

        if( nReceived != bufferSize )
        {
            isReceived = FALSE;
        }
    }

    return isReceived;
}