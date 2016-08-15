# Copyright 2015 refractionPOINT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import re
import datetime
from collections import OrderedDict
import collections
import functools
from functools import wraps
import inspect
from contextlib import contextmanager

from beach.actor import Actor
rSequence = Actor.importLib( 'rpcm', 'rSequence' )

import gevent.lock

import hmac, base64, struct, hashlib, time, string, random

def _xm_( o, path, isWildcardDepth = False ):
    def _isDynamicType( e ):
        eType = type( e )
        return issubclass( eType, dict ) or issubclass( eType, list ) or issubclass( eType, tuple )

    def _isListType( e ):
        eType = type( e )
        return issubclass( eType, list ) or issubclass( eType, tuple )

    def _isSeqType( e ):
        eType = type( e )
        return issubclass( eType, dict )

    result = []
    oType = type( o )

    if type( path ) is str or type( path ) is unicode:
        tokens = [ x for x in path.split( '/' ) if x != '' ]
    else:
        tokens = path

    if issubclass( oType, dict ):
        isEndPoint = False
        if 0 != len( tokens ):
            if 1 == len( tokens ):
                isEndPoint = True

            curToken = tokens[ 0 ]

            if '*' == curToken:
                if 1 < len( tokens ):
                    result = _xm_( o, tokens[ 1 : ], True )
            elif '?' == curToken:
                if 1 < len( tokens ):
                    result = []
                    for elem in o.itervalues():
                        if _isDynamicType( elem ):
                            result += _xm_( elem, tokens[ 1 : ], False )

            elif o.has_key( curToken ):
                if isEndPoint:
                    result = [ o[ curToken ] ] if not _isListType( o[ curToken ] ) else o[ curToken ]
                elif _isDynamicType( o[ curToken ] ):
                    result = _xm_( o[ curToken ], tokens[ 1 : ] )

            if isWildcardDepth:
                tmpTokens = tokens[ : ]
                for elem in o.itervalues():
                    if _isDynamicType( elem ):
                        result += _xm_( elem, tmpTokens, True )
    elif issubclass( oType, list ) or oType is tuple:
        result = []
        for elem in o:
            if _isDynamicType( elem ):
                result += _xm_( elem, tokens )

    return result

def _x_( o, path, isWildcardDepth = False ):
    r = _xm_( o, path, isWildcardDepth )
    if 0 != len( r ):
        r = r[ 0 ]
    else:
        r = None
    return r

def exeFromPath( path, agent = None ):
    if path is None:
        return None
    if agent is None or agent.isWindows():
        i = path.rfind( '\\' )
        j = path.rfind( '/' )
        i = max( i, j )
        if -1 != i:
            exeName = path[ i + 1 : ]
        else:
            exeName = path
    else:
        i = path.rfind( '/' )
        if -1 != i:
            exeName = path[ i + 1 : ]
        else:
            exeName = path
    return exeName

def hexDump( src, length = 8 ):
    result = []
    for i in xrange( 0, len( src ), length ):
       s = src[ i : i + length ]
       hexa = ' '.join( [ "%02X" % ord( x ) for x in s ] )
       printable = s.translate( ''.join( [ ( len( repr( chr( x ) ) ) == 3 ) and chr( x ) or '.' for x in range( 256 ) ] ) )
       result.append( "%04X   %-*s   %s\n" % ( i, length * 3, hexa, printable ) )
    return ''.join( result )

class HcpModuleId( object ):
    BOOTSTRAP = 0
    HCP = 1
    HBS = 2
    TEST = 3
    AAD = 4
    KERNEL_ACQ = 5

class HbsCollectorId ( object ):
    EXFIL = 0
    PROCESS_TRACKER = 1
    DNS_TRACKER = 2
    CODE_IDENT = 3
    NETWORK_TRACKER = 4
    HIDDEN_MODULE = 5
    MODULE_TRACKER = 6
    FILE_TRACKER = 7
    NETWORK_SUMMARY = 8
    FILE_FORENSIC = 9
    MEMORY_FORENSIC = 10
    OS_FORENSIC = 11
    _AVAILABLE = 12
    EXEC_OOB = 13
    TODO_CHANGEME = 14
    PROCESS_HOLLOWING = 15
    YARA = 16
    OS_TRACKER = 17
    DOC_COLLECTOR = 18
    VOLUME_TRACKER = 18

    lookup = {
        0 : 'EXFIL',
        1 : 'PROCESS_TRACKER',
        2 : 'DNS_TRACKER',
        3 : 'CODE_IDENT',
        4 : 'NETWORK_TRACKER',
        5 : 'HIDDEN_MODULE',
        6 : 'MODULE_TRACKER',
        7 : 'FILE_TRACKER',
        8 : 'NETWORK_SUMMARY',
        9 : 'FILE_FORENSIC',
        10 : 'MEMORY_FORENSIC',
        11 : 'OS_FORENSIC',
        12 : '_AVAILABLE',
        13 : 'EXEC_OOB',
        14 : 'TODO_CHANGEME',
        15 : 'PROCESS_HOLLOWING',
        16 : 'YARA',
        17 : 'OS_TRACKER',
        18 : 'DOC_COLLECTOR'
    }

class TwoFactorAuth(object):
    def __init__( self, username = None, secret = None ):
        self._isNew = False
        if secret is None:
            secret = base64.b32encode( ''.join( random.choice( string.ascii_letters + string.digits ) for _ in range( 16 ) ) )[ 0 : 16 ]
            self._isNew = True
        self._secret = secret
        self._username = username
        
    def _get_hotp_token( self, intervals_no ):
        key = base64.b32decode( self._secret, True )
        msg = struct.pack( ">Q", intervals_no )
        h = hmac.new( key, msg, hashlib.sha1 ).digest()
        o = ord( h[ 19 ] ) & 15
        h = ( struct.unpack( ">I", h[ o : o + 4 ])[ 0 ] & 0x7fffffff ) % 1000000
        return h
    
    def _get_totp_token( self ):
        i = int( time.time() ) / 30
        return ( self._get_hotp_token( intervals_no = i - 1 ),
                 self._get_hotp_token( intervals_no = i ),
                 self._get_hotp_token( intervals_no = i + 1 ) )

    def isAuthentic( self, providedValue ):
        if self._isNew:
            return False
        tokens = self._get_totp_token()
        return ( providedValue == tokens[ 0 ] or
                 providedValue == tokens[ 1 ] or
                 providedValue == tokens[ 2 ] )
    
    def getSecret( self, asOtp = False ):
        if asOtp is False:
            return self._secret
        else:
            return 'otpauth://totp/%s@refractionPOINT-HCP?secret=%s' % ( self._username, self._secret )


def isModuleAvailable( module ):
    import imp
    try:
        imp.find_module( module )
        found = True
    except ImportError:
        found = False
    return found

re_ip_to_tuple = re.compile( '^(\d+)\.(\d+)\.(\d+)\.(\d+)$' )
def ip_to_tuple( ip ):
    global re_ip_to_tuple
    tup = None
    
    matches = re_ip_to_tuple.match( ip )
    if matches:
        matches = matches.groups( 0 )
        tup = [ matches[ 0 ], matches[ 1 ], matches[ 2 ], matches[ 3 ] ]
    
    return tup

def chunks( l, n ):
    """ Yield successive n-sized chunks from l.
    """
    tmp = None
    for i in l:
        if tmp is None:
            tmp = []
        tmp.append( i )
        if n == len( tmp ):
            yield tmp
            tmp = None
    if tmp is not None:
        yield tmp

def tsToTime( ts ):
    return datetime.datetime.fromtimestamp( int( ts ) ).strftime( '%Y-%m-%d %H:%M:%S' )

def timeToTs( timeStr ):
    return time.mktime( datetime.datetime.strptime( str( timeStr ).split( '.' )[ 0 ], '%Y-%m-%d %H:%M:%S' ).timetuple() )

def anyOf( coll, f = None ):
    ''' Like the builtin 'any' function but this will short-circuit eval.'''
    for i in coll:
        if ( f is None and i ) or ( f is not None and f( i ) ):
            return True
    return False

def allOf( coll, f ):
    ''' Like the builtin 'all' function but this will short-circuit eval.'''
    if 0 == len( coll ): return False
    for i in coll:
        if ( f is None and not i ) or ( f is not None and not f( i ) ):
            return False
    return True

def anyOfIn( c1, c2 ):
    return anyOf( c1, lambda x: x in c2 )

def traceThisLine( **kwargs ):
    ''' SImple debugging tool, will print to stderr the info on locations of caller of this function as well as any keyword arguments you passed to it.'''
    ( frame, filename, line_number, function_name, lines, index ) = inspect.getouterframes( inspect.currentframe() )[ 1 ]
    sys.stderr.write( "%s - %s::%s : %s =  %s\n" % ( time.time(), filename, function_name, line_number, str( kwargs ) ) )
    sys.stderr.flush()
    

@contextmanager
def file_lock( lock_file ):
    ''' Designed to be used with the "with" operator.
        with file_lock( "/tmp/myfile" ):
            print( "some stuff" )
    '''
    if os.path.exists(lock_file):
        print 'Only one script can run at once. '\
              'Script is locked with %s' % lock_file
        sys.exit(-1)
    else:
        open(lock_file, 'w').write("1")
        try:
            yield
        finally:
            os.remove(lock_file)

def timedFunction( f ):
    ''' Decorator to do basic timing over a function. '''
    @wraps( f )
    def wrapped( *args, **kwargs ):
        start = time.time()
        r = f( *args, **kwargs )
        print( "%s: %s" % ( f.__name__, time.time() - start ) )
        return r
    return wrapped

class Mutex( object ):
    def __init__( self ):
        self._sem = gevent.lock.BoundedSemaphore( value = 1 )

    def lock( self, timeout = None ):
        return self._sem.acquire( timeout = timeout )

    def unlock( self ):
        return self._sem.release()

class RWLock( object ):
    def __init__( self, nReaders ):
        self._nReaders = nReaders
        self._sem = gevent.lock.BoundedSemaphore( value = nReaders )

    def rLock( self, timeout = None ):
        return self._sem.acquire( timeout = timeout )

    def rUnlock( self ):
        return self._sem.release()

    def wLock( self, timeout = None ):
        nLocked = 0
        for n in range( self._nReaders ):
            if self._sem.acquire( timeout = timeout ):
                nLocked += 1
        if nLocked != self._nReaders:
            for n in range( nLocked ):
                self._sem.release()
            return False
        else:
            return True

    def wUnlock( self ):
        for n in range( self._nReaders ):
            self._sem.release()

class AgentId( object ):
    
    re_agent_id = re.compile( '^([a-fA-F0-9]+)\.([a-fA-F0-9]+)\.([a-fA-F0-9]+)\.([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])(?:\.([a-fA-F0-9]+))?$' )
    
    def __init__( self, seq, isWithoutConfig = False ):
        self.org = 0xFF
        self.subnet = 0xFF
        self.unique = 0xFFFFFFFF
        self.platform = 0xFF
        self.config = 0xFF
        
        self.isWithoutConfig = isWithoutConfig
        
        self.isValid = False
    
        if type( seq ) is rSequence or type( seq ) is dict:
            if ( 'base.HCP_ID_ORG' in seq and # HCP_ID_ORG
                 'base.HCP_ID_SUBNET' in seq and # HCP_ID_SUBNET
                 'base.HCP_ID_UNIQUE' in seq and # HCP_ID_UNIQUE
                 'base.HCP_ID_PLATFORM' in seq ): # HCP_ID_PLATFORM
                
                self.org = int( seq[ 'base.HCP_ID_ORG' ] )
                self.subnet = int( seq[ 'base.HCP_ID_SUBNET' ] )
                self.unique = int( seq[ 'base.HCP_ID_UNIQUE' ] )
                self.platform = int( seq[ 'base.HCP_ID_PLATFORM' ] )
                
                if not isWithoutConfig:
                    if 'base.HCP_ID_CONFIG' in seq: # HCP_ID_CONFIG
                        self.config = int( seq[ 'base.HCP_ID_CONFIG' ] )
                
                self.isValid = True
            elif ( 'org' in seq and
                   'subnet' in seq and
                   'uniqueid' in seq and
                   'platform' in seq ):
                self.org = int( seq[ 'org' ] )
                self.subnet = int( seq[ 'subnet' ] )
                self.unique = int( seq[ 'uniqueid' ] )
                self.platform = int( seq[ 'platform' ] )
                
                if not isWithoutConfig:
                    if 'config' in seq:
                        self.config = int( seq[ 'config' ] )
                self.isValid = True
                
        elif type( seq ) is str or type( seq ) is unicode:
            matches = self.re_agent_id.match( seq )
            if matches is not None:
                matches = matches.groups( 0 )
                self.org = int( matches[ 0 ], 16 )
                self.subnet = int( matches[ 1 ], 16 )
                self.unique = int( matches[ 2 ], 16 )
                tmp_cpu = int( matches[ 3 ], 16 )
                tmp_major = int( matches[ 4 ], 16 )
                tmp_minor = int( matches[ 5 ], 16 )
                self.platform = ( ( ( tmp_cpu & 3 ) << 6 ) | ( ( tmp_major & 7 ) << 3 ) | ( tmp_minor & 7 ) )
                if 0 != matches[ 6 ]:
                    if not isWithoutConfig:
                        self.config = int( matches[ 6 ], 16 )
                
                self.isValid = True
        elif type( seq ) is list or type( seq ) is tuple:
            self.org = int( seq[ 0 ] )
            self.subnet = int( seq[ 1 ] )
            self.unique = int( seq[ 2 ] )
            if 3 < len( seq ):
                self.platform = int( seq[ 3 ] )
                if 5 == len( seq ):
                    if not isWithoutConfig:
                        self.config = int( seq[ 4 ] )
                self.isValid = True
        elif type( seq ) is AgentId:
            self.org = int( seq.org )
            self.subnet = int( seq.subnet )
            self.unique = int( seq.unique )
            self.platform = int( seq.platform )
            if not isWithoutConfig:
                self.config = int( seq.config ) if seq.config is not None else None
            self.isValid = seq.isValid

    def asWhere( self, isSimpleOnly = False ):
        filt = []
        filtValues = []

        if self.org != 0xFF:
            filt.append( 'org = %s' )
            filtValues.append( self.org )
        if self.subnet != 0xFF:
            filt.append( 'subnet = %s' )
            filtValues.append( self.subnet )
        if self.unique != 0xFFFFFFFF:
            filt.append( 'unique = %s' )
            filtValues.append( self.unique )
        if not isSimpleOnly:
            if self.platform != 0xFF:
                filt.append( 'platform = %s' )
                filtValues.append( self.platform )
            if self.config != 0xFF:
                filt.append( 'config = %s' )
                filtValues.append( self.config )

        return ( ' AND '.join( filt ), filtValues )

    def asString( self, isInvariable = False ) :
        if self.isValid:
            arch = self.getArchPlatform()
            major = self.getMajorPlatform()
            minor = self.getMinorPlatform()
            if 3 == arch:
                arch = 0xF
            if 7 == major:
                major = 0xF
            if 7 == minor:
                minor = 0xF
            s = '%s.%s.%s.%s%s%s' % ( hex( self.org )[ 2 : ],
                                      hex( self.subnet )[ 2 : ],
                                      hex( self.unique )[ 2 : ],
                                      hex( arch )[ 2 : ],
                                      hex( major )[ 2 : ],
                                      hex( minor )[ 2 : ] )

            if not self.isWithoutConfig and not isInvariable:
                if self.config is not None:
                    s += '.%s' % hex( self.config )[ 2 : ]
        else:
            s = ''

        return s

    def __str__( self ):
        return self.asString( isInvariable = False )

    def __repr__( self ):
        return 'AgentId( %s )' % self.asString( isInvariable = False )
    
    def invariableToString( self ):
        return self.asString( isInvariable = True )
        
    def __eq__( self, a ):
        isEqual = False
        
        if type( a ) is AgentId:
            if self.org == a.org and self.subnet == a.subnet and self.unique == a.unique and self.platform == a.platform:
                if ( None == self.config and None == a.config ) or ( self.config == a.config ):
                    isEqual = True
        elif type( a ) is str or type( a ) is unicode:
            if str( self ) == a:
                isEqual = True
        
        return isEqual
    
    def __ne__( self, a ):
        return not self.__eq__( a )
    
    def inSubnet( self, subnet ):
        isMatch = False
        
        if self == subnet:
            isMatch = True
        else:
            if ( ( self.org == subnet.org or subnet.org == 0xFF ) and
                 ( self.subnet == subnet.subnet or subnet.subnet == 0xFF ) and
                 ( self.unique == subnet.unique or subnet.unique == 0xFFFFFFFF ) and
                 ( self.getArchPlatform() == subnet.getArchPlatform() or 3 == subnet.getArchPlatform() ) and
                 ( self.getMajorPlatform() == subnet.getMajorPlatform() or 7 == subnet.getMajorPlatform() ) and
                 ( self.getMinorPlatform() == subnet.getMinorPlatform() or 7 == subnet.getMinorPlatform() ) and
                 ( self.config == subnet.config or subnet.config == 0xFF ) ):
                isMatch = True
        
        return isMatch
    
    def toJson( self ):
        j = None
        
        if self.isValid:
            j = {
                    'base.HCP_ID_ORG' : { 'tag' : 'base.HCP_ID_ORG', 'type' : 'int_8', 'value' : self.org },
                    'base.HCP_ID_SUBNET' : { 'tag' : 'base.HCP_ID_SUBNET', 'type' : 'int_8', 'value' : self.subnet },
                    'base.HCP_ID_UNIQUE' : { 'tag' : 'base.HCP_ID_UNIQUE', 'type' : 'int_32', 'value' : self.unique },
                    'base.HCP_ID_PLATFORM' : { 'tag' : 'base.HCP_ID_PLATFORM', 'type' : 'int_8', 'value' : self.platform },
                    'base.HCP_ID_CONFIG' : { 'tag' : 'base.HCP_ID_CONFIG', 'type' : 'int_8', 'value' : self.config }
                }
        
        
        return j
    
    def getMajorPlatform( self ):
        return ( self.platform & 0x38 ) >> 3

    def getArchPlatform( self ):
        return ( self.platform & 0xC0 ) >> 6

    def getMinorPlatform( self ):
        return ( self.platform & 0x07 )
    
    def isWindows( self ):
        return self.getMajorPlatform() == 0x01
    
    def isLinux( self ):
        return self.getMajorPlatform() == 0x05
    
    def isMacOSX( self ):
        return self.getMajorPlatform() == 0x02
    
    def isIos( self ):
        return self.getMajorPlatform() == 0x03
    
    def isAndroid( self ):
        return self.getMajorPlatform() == 0x04
    
    def isX86( self ):
        return self.getArchPlatform() == 0x01

    def isX64( self ):
        return self.getArchPlatform() == 0x02

    def isWildcarded( self ):
        return ( 0xFF == self.org or
                 0xFF == self.subnet or
                 0xFFFFFFFF == self.unique or
                 3 == self.getArchPlatform() or
                 7 == self.getMajorPlatform() or
                 7 == self.getMinorPlatform() )


class RingCache( object ):
    
    def __init__( self, maxEntries = 100, isAutoAdd = False ):
        self.max = maxEntries
        self.d = OrderedDict()
        self.isAutoAdd = isAutoAdd
    
    def add( self, k, v = None ):
        if self.max <= len( self.d ):
            self.d.popitem( last = False )
        if k in self.d:
            del( self.d[ k ] )
        self.d[ k ] = v
    
    def get( self, k ):
        return self.d[ k ]
    
    def remove( self, k ):
        del( self.d[ k ] )
    
    def __contains__( self, k ):
        if k in self.d:
            v = self.d[ k ]
            del( self.d[ k ] )
            self.d[ k ] = v
            return True
        else:
            if self.isAutoAdd:
                self.add( k )
            return False
    
    def __len__( self ):
        return len( self.d )
    
    def __repr__( self ):
        return self.d.__repr__()

class ringcached( object ):
    '''
    Ring Caching Decorator
    '''
    def __init__( self, func, maxEntries = 100 ):
        self.func = func
        self.maxEntries = maxEntries
        self.cache = RingCache( maxEntries )
        
    def __call__( self, *args ):
        if not isinstance( args, collections.Hashable ):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func( *args )
        
        if args in self.cache:
            return self.cache.get( args )
        
        else:
            value = self.func( *args )
            self.cache.add( args, value )
            return value
        
    def __repr__( self ):
        return self.func.__doc__
    def __get__( self, obj, objtype ):
        return functools.partial( self.__call__, obj )

def synchronized( lock = None ):
    '''Synchronization decorator.'''
    
    if lock is None:
        import threading
        lock = threading.Lock()

    def wrap(f):
        def new_function(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return new_function
    return wrap

class HcpOperations:
    LOAD_MODULE = 1
    UNLOAD_MODULE = 2
    SET_HCP_ID = 3
    SET_GLOBAL_TIME = 4
    QUIT = 5

class PooledResource( object ):
    def __init__( self, resourceFactoryFunc, maxResources = None ):
        self._factory = resourceFactoryFunc
        self._resources = []
        self._maxResources = maxResources
        self._curResources = 0

    def acquire( self ):
        res = None
        if 0 != len( self._resources ):
            res = self._resources.pop()
        elif self._maxResources is None or self._maxResources > self._curResources:
            res = self._factory()
        return res

    def release( self, resource ):
        self._resources.append( resource )

    @contextmanager
    def anInstance( self, releaseOnException = False ):
        try:
            db = self.acquire()
            yield db
        except:
            if releaseOnException:
                self.release( db )
        else:
            self.release( db )

class CreateOnAccess( object ):
    def __init__( self, toCall, *args, **kwargs ):
        self._toCall = toCall
        self._args = args
        self._kwargs = kwargs
        self._instance = None
    def __getattr__(self, item):
        if self._instance is None:
            self._instance = self._toCall( *self._args, **self._kwargs )
        return getattr( self._instance, item )