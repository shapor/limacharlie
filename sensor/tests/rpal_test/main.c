#include <rpal/rpal.h>
#include <Basic.h>

#define RPAL_FILE_ID   96
#define _TEST_MAJOR_1   6

void test_memoryLeaks(void)
{
    RU32 memUsed = 0;

    rpal_Context_cleanup();

    memUsed = rpal_memory_totalUsed();

    CU_ASSERT_EQUAL( memUsed, 0 );

    if( 0 != memUsed )
    {
        rpal_debug_critical( "Memory leak: %d bytes.\n", memUsed );
        printf( "\nMemory leak: %d bytes.\n", memUsed );

        rpal_memory_findMemory();
    }
}

void test_strings(void)
{
    RNATIVECHAR tmpString[] = RNATIVE_LITERAL( "C:\\WINDOWS\\SYSTEM32\\SVCHOST.EXE" );
    CU_ASSERT_EQUAL( rpal_string_strlen( tmpString ), ARRAY_N_ELEM( tmpString ) - 1 );
}

void test_events(void)
{
    rEvent evt = NULL;
    evt = rEvent_create( TRUE );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( evt, NULL );

    CU_ASSERT_FALSE( rEvent_wait( evt, 0 ) );
    CU_ASSERT_TRUE( rEvent_set( evt ) );
    // Manual reset so it should still be up
    CU_ASSERT_TRUE( rEvent_wait( evt, 0 ) );
    CU_ASSERT_TRUE( rEvent_wait( evt, 0 ) );
    CU_ASSERT_TRUE( rEvent_unset( evt ) );
    CU_ASSERT_FALSE( rEvent_wait( evt, 0 ) );

    rEvent_free( evt );
    
    evt = rEvent_create( FALSE );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( evt, NULL );
    
    CU_ASSERT_FALSE( rEvent_wait( evt, 0 ) );
    CU_ASSERT_TRUE( rEvent_set( evt ) );
    // Auto reset so it should still be down
    CU_ASSERT_TRUE( rEvent_wait( evt, 0 ) );
    CU_ASSERT_FALSE( rEvent_wait( evt, 0 ) );
    
    CU_ASSERT_TRUE( rEvent_set( evt ) );
    CU_ASSERT_TRUE( rEvent_unset( evt ) );
    CU_ASSERT_FALSE( rEvent_wait( evt, 0 ) );
    
    rEvent_free( evt );
}

void test_handleManager(void)
{
    RU32 dummy1 = 42;
    RU32* test = NULL;
    rHandle hDummy1 = RPAL_HANDLE_INIT;
    RBOOL isDestroyed = FALSE;
    
    hDummy1 = rpal_handleManager_create( _TEST_MAJOR_1, (RU32)RPAL_HANDLE_INVALID, &dummy1, NULL );

    CU_ASSERT_NOT_EQUAL_FATAL( hDummy1.h, RPAL_HANDLE_INVALID );

    CU_ASSERT_TRUE_FATAL( rpal_handleManager_open( hDummy1, (RPVOID*)&test ) );

    CU_ASSERT_EQUAL( *test, dummy1 );

    CU_ASSERT_TRUE( rpal_handleManager_close( hDummy1, &isDestroyed ) );
    CU_ASSERT_FALSE_FATAL( isDestroyed );
    CU_ASSERT_TRUE( rpal_handleManager_close( hDummy1, &isDestroyed ) );
    CU_ASSERT_TRUE_FATAL( isDestroyed );
    
}

void test_blob(void)
{
    rBlob blob = NULL;
    RU8 refBuff[] = { 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07 };
    RU8 trimBuff1[] = { 0x01, 0x02, 0x07 };
    RU8 trimBuff2[] = { 0x02, 0x07 };
    RU8 trimBuff3[] = { 0x02 };
    RPU8 tmpBuff = NULL;

    blob = rpal_blob_create( 0, 10 );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( blob, NULL );

    CU_ASSERT_TRUE( rpal_blob_add( blob, refBuff, sizeof( refBuff ) ) );

    tmpBuff = rpal_blob_getBuffer( blob );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( tmpBuff, NULL );

    CU_ASSERT_EQUAL( rpal_memory_memcmp( tmpBuff, rpal_blob_getBuffer( blob ), sizeof( refBuff ) ), 0 );

    CU_ASSERT_TRUE( rpal_blob_remove( blob, 2, 4 ) );
    CU_ASSERT_EQUAL( rpal_memory_memcmp( trimBuff1, rpal_blob_getBuffer( blob ), sizeof( trimBuff1 ) ), 0 );

    CU_ASSERT_TRUE( rpal_blob_remove( blob, 0, 1 ) );
    CU_ASSERT_EQUAL( rpal_memory_memcmp( trimBuff2, rpal_blob_getBuffer( blob ), sizeof( trimBuff2 ) ), 0 );

    CU_ASSERT_TRUE( rpal_blob_remove( blob, 1, 1 ) );
    CU_ASSERT_EQUAL( rpal_memory_memcmp( trimBuff3, rpal_blob_getBuffer( blob ), sizeof( trimBuff3 ) ), 0 );

    CU_ASSERT_FALSE( rpal_blob_remove( blob, 2, 2 ) );

    rpal_blob_free( blob );
}

RBOOL
    _dummyStackFree
    (
        RPU32 pRu32
    )
{
    RBOOL isSuccess = FALSE;

    if( NULL != pRu32 )
    {
        *pRu32 = 0;
        isSuccess = TRUE;
    }

    return isSuccess;
}

void test_stack(void)
{
    rStack stack = NULL;
    RU32 val1 = 1;
    RU32 val2 = 42;
    RU32 val3 = 666;
    RU32 val4 = 70000;
    RU32 test = 0;

    stack = rStack_new( sizeof( RU32 ) );

    CU_ASSERT_PTR_NOT_EQUAL_FATAL( stack, NULL );


    CU_ASSERT_TRUE( rStack_push( stack, &val1 ) );
    CU_ASSERT_TRUE( rStack_push( stack, &val2 ) );
    CU_ASSERT_TRUE( rStack_push( stack, &val3 ) );

    CU_ASSERT_FALSE( rStack_isEmpty( stack ) );

    CU_ASSERT_TRUE( rStack_pop( stack, &test ) );
    CU_ASSERT_EQUAL( test, val3 );

    CU_ASSERT_TRUE( rStack_push( stack, &val4 ) );

    CU_ASSERT_TRUE( rStack_pop( stack, &test ) );
    CU_ASSERT_EQUAL( test, val4 );
    CU_ASSERT_TRUE( rStack_pop( stack, &test ) );
    CU_ASSERT_EQUAL( test, val2 );
    CU_ASSERT_TRUE( rStack_pop( stack, &test ) );
    CU_ASSERT_EQUAL( test, val1 );

    CU_ASSERT_FALSE( rStack_pop( stack, &test ) );
    CU_ASSERT_TRUE( rStack_isEmpty( stack ) );

    CU_ASSERT_TRUE( rStack_free( stack, (rStack_freeFunc)_dummyStackFree ) );
}

void test_queue(void)
{
    rQueue q = NULL;

    RU32 i1 = 1;
    RU32 i2 = 2;
    RU32 i3 = 3;
    RU32 i4 = 4;
    RU32 i5 = 5;

    RU32* pI = 0;
    RU32 iSize = 0;

    CU_ASSERT_TRUE( rQueue_create( &q, NULL, 3 ) );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( q, NULL );

    CU_ASSERT_TRUE( rQueue_add( q, &i1, sizeof( i1 ) ) );
    CU_ASSERT_TRUE( rQueue_add( q, &i2, sizeof( i2 ) ) );
    CU_ASSERT_TRUE( rQueue_add( q, &i3, sizeof( i3 ) ) );
    CU_ASSERT_FALSE( rQueue_addEx( q, &i4, sizeof( i4 ), FALSE ) );
    CU_ASSERT_TRUE( rQueue_add( q, &i5, sizeof( i5 ) ) );

    CU_ASSERT_TRUE( rQueue_remove( q, (RPVOID*)&pI, &iSize, (10*1000) ) );
    CU_ASSERT_EQUAL( *pI, i2 );
    CU_ASSERT_EQUAL( iSize, sizeof( RU32 ) );

    CU_ASSERT_TRUE( rQueue_remove( q, (RPVOID*)&pI, &iSize, (10*1000) ) );
    CU_ASSERT_EQUAL( *pI, i3 );
    CU_ASSERT_EQUAL( iSize, sizeof( RU32 ) );

    CU_ASSERT_TRUE( rQueue_remove( q, (RPVOID*)&pI, &iSize, (10*1000) ) );
    CU_ASSERT_EQUAL( *pI, i5 );
    CU_ASSERT_EQUAL( iSize, sizeof( RU32 ) );

    CU_ASSERT_TRUE( rQueue_isEmpty( q ) );
    CU_ASSERT_FALSE( rQueue_isFull( q ) );

    CU_ASSERT_FALSE( rQueue_remove( q, (RPVOID*)&pI, &iSize, 10 ) );

    rQueue_free( q );
}

void test_circularbuffer(void)
{
    rCircularBuffer cb = NULL;

    RU32 i1 = 1;
    RU32 i2 = 2;
    RU32 i3 = 3;
    RU32 i4 = 4;
    RU32 i5 = 5;

    cb = rpal_circularbuffer_new( 3, sizeof( RU32 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( cb, NULL );

    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_last( cb ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 0 ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 2 ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 3 ), NULL );

    CU_ASSERT_TRUE( rpal_circularbuffer_add( cb, &i1 ) );

    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 0 ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 1 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_last( cb ), NULL );

    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 0 ), 1 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_last( cb ), 1 );

    CU_ASSERT_TRUE( rpal_circularbuffer_add( cb, &i2 ) );

    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 0 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 1 ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 2 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_last( cb ), NULL );

    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 0 ), 1 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 1 ), 2 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_last( cb ), 2 );

    CU_ASSERT_TRUE( rpal_circularbuffer_add( cb, &i3 ) );
    CU_ASSERT_TRUE( rpal_circularbuffer_add( cb, &i4 ) );
    CU_ASSERT_TRUE( rpal_circularbuffer_add( cb, &i5 ) );

    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 0 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 1 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_get( cb, 2 ), NULL );
    CU_ASSERT_PTR_EQUAL( rpal_circularbuffer_get( cb, 3 ), NULL );
    CU_ASSERT_PTR_NOT_EQUAL( rpal_circularbuffer_last( cb ), NULL );

    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 0 ), 4 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 1 ), 5 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_get( cb, 2 ), 3 );
    CU_ASSERT_EQUAL( *(RU32*)rpal_circularbuffer_last( cb ), 5 );

    rpal_circularbuffer_free( cb );
}

void test_strtok(void)
{
    RNATIVECHAR testStr[] = { RNATIVE_LITERAL( "/this/is/a/test/path" ) };
    RNATIVECHAR token = RNATIVE_LITERAL( '/' );
    RNATIVESTR state = NULL;
    RNATIVESTR tmp = NULL;

    tmp = rpal_string_strtok( testStr, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "" ) ), 0 );

    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "this" ) ), 0 );
    
    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "is" ) ), 0 );
    
    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "a" ) ), 0 );
    
    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "test" ) ), 0 );
    
    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_NOT_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( tmp, RNATIVE_LITERAL( "path" ) ), 0 );

    
    tmp = rpal_string_strtok( NULL, token, &state );
    CU_ASSERT_PTR_EQUAL( tmp, NULL );

    CU_ASSERT_EQUAL( rpal_string_strcmp( testStr, RNATIVE_LITERAL("/this/is/a/test/path") ), 0 );
}

void test_strmatch(void)
{
    RNATIVESTR pattern1 = RNATIVE_LITERAL("this?complex*pattern?");
    RNATIVESTR pattern2 = RNATIVE_LITERAL( "this?complex*pattern+" );
    RNATIVESTR pattern3 = RNATIVE_LITERAL( "this?complex+pattern*" );
    RNATIVESTR pattern4 = RNATIVE_LITERAL( "this\\?escaped\\pattern" );

    RNATIVESTR test1 = RNATIVE_LITERAL( "thiscomplexpattern" );
    RNATIVESTR test2 = RNATIVE_LITERAL( "this1complex1234pattern" );
    RNATIVESTR test3 = RNATIVE_LITERAL( "this2complex123456pattern1" );
    RNATIVESTR test4 = RNATIVE_LITERAL( "this2complex123456pattern123" );
    RNATIVESTR test5 = RNATIVE_LITERAL( "this1complexpattern" );

    RNATIVESTR test6 = RNATIVE_LITERAL( "this?escaped\\pattern" );
    RNATIVESTR test7 = RNATIVE_LITERAL( "this1escapedpattern" );

    CU_ASSERT_FALSE( rpal_string_match( pattern1, test1, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern1, test2, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern1, test3, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern1, test4, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern1, test5, TRUE ) );

    CU_ASSERT_FALSE( rpal_string_match( pattern2, test1, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern2, test2, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern2, test3, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern2, test4, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern2, test5, TRUE ) );

    CU_ASSERT_FALSE( rpal_string_match( pattern3, test1, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern3, test2, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern3, test3, TRUE ) );
    CU_ASSERT_TRUE( rpal_string_match( pattern3, test4, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern3, test5, TRUE ) );

    CU_ASSERT_TRUE( rpal_string_match( pattern4, test6, TRUE ) );
    CU_ASSERT_FALSE( rpal_string_match( pattern4, test7, TRUE ) );
}

void test_dir(void)
{
    rDir hDir = NULL;
    rFileInfo info = {0};

    CU_ASSERT_TRUE( rDir_open( RNATIVE_LITERAL( "./" ), &hDir ) );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( hDir, NULL );

    while( rDir_next( hDir, &info ) )
    {
        CU_ASSERT_NOT_EQUAL( info.filePath[ 0 ], 0 );
        CU_ASSERT_PTR_NOT_EQUAL( info.fileName, NULL );
        if( !IS_FLAG_ENABLED( info.attributes, RPAL_FILE_ATTRIBUTE_DIRECTORY ) )
        {
            CU_ASSERT_NOT_EQUAL( info.size, 0 );
        }
    }
    
    rDir_close( hDir );
}

void test_crawler(void)
{
    rDirCrawl hCrawl = NULL;
    rFileInfo info = {0};
#ifdef RPAL_PLATFORM_WINDOWS
    RPWCHAR fileArr[] = { _WCH("*.dll"), _WCH("*.exe"), NULL };
    hCrawl = rpal_file_crawlStart( _WCH("C:\\test\\"), fileArr, 2 );
#elif defined( RPAL_PLATFORM_LINUX )
    RNATIVESTR fileArr[] = { RNATIVE_LITERAL("*.pub"), RNATIVE_LITERAL("*.txt"), NULL };
    hCrawl = rpal_file_crawlStart( RNATIVE_LITERAL("/home/server/"), fileArr, 2 );
#endif
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( hCrawl, NULL );
    
    while( rpal_file_crawlNextFile( hCrawl, &info ) )
    {
        rpal_debug_info( "FILE" );
        printf( RF_STR_A "\n", info.filePath );
    }
    
    rpal_file_crawlStop( hCrawl );
}


void test_file(void)
{
    rFile hFile = NULL;
    RWCHAR testBuff[] = _WCH("testing...");
    RWCHAR outBuff[ ARRAY_N_ELEM( testBuff ) ] = {0};

    CU_ASSERT_TRUE_FATAL( rFile_open( RNATIVE_LITERAL("./testfile.dat"), &hFile, RPAL_FILE_OPEN_ALWAYS | RPAL_FILE_OPEN_WRITE ) );
    CU_ASSERT_TRUE( rFile_write( hFile, sizeof( testBuff ), &testBuff ) );
    rFile_close( hFile );
    CU_ASSERT_TRUE_FATAL( rFile_open( RNATIVE_LITERAL( "./testfile.dat" ), &hFile, RPAL_FILE_OPEN_EXISTING | RPAL_FILE_OPEN_READ ) );
    CU_ASSERT_TRUE( rFile_read( hFile, sizeof( outBuff ), &outBuff ) );
    rFile_close( hFile );
    CU_ASSERT_EQUAL( rpal_memory_memcmp( testBuff, outBuff, sizeof( testBuff ) ), 0 );

}


void test_bloom( void )
{
    rBloom b = NULL;

    RU32 i1 = 1;
    RU32 i2 = 2;
    RU32 i3 = 3;
    RU32 i4 = 4;

    RPVOID buff = NULL;
    RU32 size = 0;

    b = rpal_bloom_create( 100, 0.001 );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( b, NULL );

    CU_ASSERT_TRUE( rpal_bloom_add( b, &i1, sizeof( i1 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i1, sizeof( i1 ) ) );

    CU_ASSERT_TRUE( rpal_bloom_add( b, &i2, sizeof( i2 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i2, sizeof( i2 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i1, sizeof( i1 ) ) );

    CU_ASSERT_FALSE( rpal_bloom_present( b, &i3, sizeof( i3 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_addIfNew( b, &i3, sizeof( i3 ) ) );
    CU_ASSERT_FALSE( rpal_bloom_addIfNew( b, &i3, sizeof( i3 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i3, sizeof( i3 ) ) );

    CU_ASSERT_TRUE( rpal_bloom_serialize( b, (RPU8*)&buff, &size ) );
    rpal_bloom_destroy( b );
    b = rpal_bloom_deserialize( buff, size );
    rpal_memory_free( buff );
    CU_ASSERT_PTR_NOT_EQUAL_FATAL( b, NULL );

    CU_ASSERT_TRUE( rpal_bloom_present( b, &i1, sizeof( i1 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i2, sizeof( i2 ) ) );
    CU_ASSERT_TRUE( rpal_bloom_present( b, &i3, sizeof( i3 ) ) );
    CU_ASSERT_FALSE( rpal_bloom_present( b, &i4, sizeof( i4 ) ) );
    
    rpal_bloom_destroy( b );
}


RU32 g_tp_total_test_res = 0;
RU32 g_tp_total_scheduled_test_res = 0;

RPU32
    tp_test
    (
        rEvent stopEvt,
        RPU32 pNum
    )
{
    UNREFERENCED_PARAMETER( stopEvt );
    g_tp_total_test_res++;
    return pNum;
}

RPU32
    tp_testLong
    (
        rEvent stopEvt,
        RPU32 pNum
    )
{
    UNREFERENCED_PARAMETER( stopEvt );
    rpal_thread_sleep( MSEC_FROM_SEC( 5 ) );
    g_tp_total_test_res++;
    return pNum;
}

RPU32
    tp_testScheduleOnce
    (
        rEvent stopEvt,
        RPU32 pNum
    )
{
    UNREFERENCED_PARAMETER( stopEvt );
    g_tp_total_scheduled_test_res++;
    return pNum;
}


RPU32
    tp_testSchedule
    (
        rEvent stopEvt,
        RPU32 pNum
    )
{
    UNREFERENCED_PARAMETER( stopEvt );
    g_tp_total_scheduled_test_res++;
    return pNum;
}

void test_threadpool(void)
{
    rThreadPool pool = NULL;

    RU32 n1 = 1;
    RU32 n2 = 2;
    RU32 n3 = 3;
    RU32 n4 = 4;
    RU32 n5 = 5;
    RU32 n6 = 6;
    RU32 n7 = 7;

    pool = rThreadPool_create( 3, 10, 60 );

    CU_ASSERT_PTR_NOT_EQUAL_FATAL( pool, NULL );

    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_testLong, &n1 ) );

    CU_ASSERT_FALSE( rThreadPool_isIdle( pool ) );

    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n1 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n2 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n3 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n4 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n5 ) );

    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n1 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n2 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n3 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n4 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n5 ) );

    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n1 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n2 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n3 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n4 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n5 ) );

    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n1 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n2 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n3 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n4 ) );
    CU_ASSERT_TRUE( rThreadPool_task( pool, (rpal_thread_pool_func)tp_test, &n5 ) );

    rpal_thread_sleep( MSEC_FROM_SEC( 10 ) );

    CU_ASSERT_TRUE( rThreadPool_isIdle( pool ) );

    rThreadPool_scheduleOneTime( pool, 
                                 rpal_time_getGlobal() + 2 ,
                                 (rpal_thread_pool_func)tp_testScheduleOnce, 
                                 &n6 );
    rThreadPool_scheduleRecurring( pool, 2,(rpal_thread_pool_func)tp_testSchedule, &n7, TRUE );

    rpal_thread_sleep( MSEC_FROM_SEC( 5 ) );

    rThreadPool_destroy( pool, TRUE );

    CU_ASSERT_EQUAL( g_tp_total_test_res, 21 );
    CU_ASSERT_TRUE( g_tp_total_scheduled_test_res >= 3 || g_tp_total_scheduled_test_res  <= 4 );
}


void test_sortsearch( void )
{
    RU32 toSort[] = { 2, 6, 7, 8, 32, 10, 14, 64, 99, 100 };
    RU32 sorted[] = { 2, 6, 7, 8, 10, 14, 32, 64, 99, 100 };
    RU32 toFind = 7;
    RU32 toFindRel = 9;
    RU32 toFindRel2 = 3;
    RU32 toFindRel3 = 98;
    RU32 toFindRel4 = 150;
    RU32 toFindRel5 = 0;
    RU32 i = 0;

    CU_ASSERT_TRUE( rpal_sort_array( toSort, 
                                     ARRAY_N_ELEM( toSort ), 
                                     sizeof( RU32 ), 
                                     (rpal_ordering_func)rpal_order_RU32 ) );

    for( i = 0; i < ARRAY_N_ELEM( toSort ); i++ )
    {
        CU_ASSERT_EQUAL( toSort[ i ], sorted[ i ] );
    }

    CU_ASSERT_EQUAL( 2, rpal_binsearch_array( toSort, 
                                              ARRAY_N_ELEM( toSort ), 
                                              sizeof( RU32 ), 
                                              &toFind, 
                                              (rpal_ordering_func)rpal_order_RU32 ) );

    CU_ASSERT_EQUAL( -1, rpal_binsearch_array( toSort,
                                               ARRAY_N_ELEM( toSort ),
                                               sizeof( RU32 ),
                                               &toFindRel,
                                               (rpal_ordering_func)rpal_order_RU32 ) );

    CU_ASSERT_EQUAL( 2, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFind,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      TRUE ) );

    CU_ASSERT_EQUAL( 2, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFind,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      FALSE ) );

    CU_ASSERT_EQUAL( 3, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      TRUE ) );

    CU_ASSERT_EQUAL( 4, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      FALSE ) );
    CU_ASSERT_EQUAL( 0, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel2,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      TRUE ) );

    CU_ASSERT_EQUAL( 1, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel2,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      FALSE ) );

    CU_ASSERT_EQUAL( 7, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel3,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      TRUE ) );

    CU_ASSERT_EQUAL( 8, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel3,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      FALSE ) );

    CU_ASSERT_EQUAL( 9, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel4,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      TRUE ) );

    CU_ASSERT_EQUAL( -1, rpal_binsearch_array_closest( toSort,
                                                       ARRAY_N_ELEM( toSort ),
                                                       sizeof( RU32 ),
                                                       &toFindRel4,
                                                       (rpal_ordering_func)rpal_order_RU32,
                                                       FALSE ) );

    CU_ASSERT_EQUAL( -1, rpal_binsearch_array_closest( toSort,
                                                       ARRAY_N_ELEM( toSort ),
                                                       sizeof( RU32 ),
                                                       &toFindRel5,
                                                       (rpal_ordering_func)rpal_order_RU32,
                                                       TRUE ) );

    CU_ASSERT_EQUAL( 0, rpal_binsearch_array_closest( toSort,
                                                      ARRAY_N_ELEM( toSort ),
                                                      sizeof( RU32 ),
                                                      &toFindRel5,
                                                      (rpal_ordering_func)rpal_order_RU32,
                                                      FALSE ) );
}


int
    main
    (
        int argc,
        char* argv[]
    )
{
    int ret = 1;

    CU_pSuite suite = NULL;
    CU_ErrorCode error = 0;

    UNREFERENCED_PARAMETER( argc );
    UNREFERENCED_PARAMETER( argv );

    if( rpal_initialize( NULL, 1 ) )
    {
        if( CUE_SUCCESS == ( error = CU_initialize_registry() ) )
        {
            if( NULL != ( suite = CU_add_suite( "rpal", NULL, NULL ) ) )
            {
                if( NULL == CU_add_test( suite, "events", test_events ) ||
                    NULL == CU_add_test( suite, "handleManager", test_handleManager ) ||
                    NULL == CU_add_test( suite, "strings", test_strings ) ||
                    NULL == CU_add_test( suite, "blob", test_blob ) ||
                    NULL == CU_add_test( suite, "stack", test_stack ) ||
                    NULL == CU_add_test( suite, "queue", test_queue ) ||
                    NULL == CU_add_test( suite, "circularbuffer", test_circularbuffer ) ||
                    NULL == CU_add_test( suite, "strtok", test_strtok ) ||
                    NULL == CU_add_test( suite, "strmatch", test_strmatch ) ||
                    NULL == CU_add_test( suite, "dir", test_dir ) ||
                    NULL == CU_add_test( suite, "crawl", test_crawler ) ||
                    NULL == CU_add_test( suite, "file", test_file ) ||
                    NULL == CU_add_test( suite, "bloom", test_bloom ) ||
                    NULL == CU_add_test( suite, "threadpool", test_threadpool ) ||
                    NULL == CU_add_test( suite, "sortsearch", test_sortsearch ) ||
                    NULL == CU_add_test( suite, "memoryLeaks", test_memoryLeaks ) )
                {
                    rpal_debug_error( "%s", CU_get_error_msg() );
                    ret = 0;
                }
                else
                {
                    CU_basic_run_tests();
                }
            }
        
            CU_cleanup_registry();
        }
        else
        {
            rpal_debug_error( "could not init cunit: %d", error );
        }
    
        rpal_Context_deinitialize();
    }
    else
    {
        printf( "error initializing rpal" );
    }

    return ret;
}

