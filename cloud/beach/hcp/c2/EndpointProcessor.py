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

from beach.actor import Actor
import gevent
from gevent.lock import Semaphore
from gevent.server import StreamServer
import os
import sys
import struct
import M2Crypto
import zlib
import uuid
import hashlib
import random
import traceback
import time
rpcm = Actor.importLib( '../utils/rpcm', 'rpcm' )
rList = Actor.importLib( '../utils/rpcm', 'rList' )
rSequence = Actor.importLib( '../utils/rpcm', 'rSequence' )
AgentId = Actor.importLib( '../utils/hcp_helpers', 'AgentId' )
HcpModuleId = Actor.importLib( '../utils/hcp_helpers', 'HcpModuleId' )
Symbols = Actor.importLib( '../Symbols', 'Symbols' )()
HcpOperations = Actor.importLib( '../utils/hcp_helpers', 'HcpOperations' )

rsa_2048_min_size = 0x100
aes_256_iv_size = 0x10
aes_256_block_size = 0x10
aes_256_key_size = 0x20
rsa_header_size = 0x100 + 0x10 # rsa_2048_min_size + aes_256_iv_size
rsa_signature_size = 0x100

class DisconnectException( Exception ):
    pass

class _ClientContext( object ):
    def __init__( self, parent, socket ):
        self.parent = parent
        self.s = socket
        self.aid = None
        self.lock = Semaphore( 1 )
        self.sKey = None
        self.sIv = None
        self.sendAes = None
        self.recvAes = None
        self.r = rpcm( isHumanReadable = True, isDebug = self.parent.log )
        self.r.loadSymbols( Symbols.lookups )

    def setKey( self, sKey, sIv ):
        self.sKey = sKey
        self.sIv = sIv
        # We disable padding and do it manually on our own
        # to bypass the problem with the API. With padding ON
        # the last call to .update actually withholds the last
        # block until the call to final is made (to apply padding)
        # but when .final is called the cipher is destroyed.
        # In our case we want to keep the cipher alive during the
        # entire session, but we can't wait indefinitely for the
        # next message to come along to "release" the previous block.
        self.sendAes = M2Crypto.EVP.Cipher( alg = 'aes_256_cbc',
                                            key = self.sKey, 
                                            iv = self.sIv, 
                                            salt = False, 
                                            key_as_bytes = False, 
                                            padding = False,
                                            op = 1 ) # 0 == ENC
        self.recvAes = M2Crypto.EVP.Cipher( alg = 'aes_256_cbc',
                                            key = self.sKey, 
                                            iv = self.sIv, 
                                            salt = False, 
                                            key_as_bytes = False, 
                                            padding = False,
                                            op = 0 ) # 0 == DEC

    def setAid( self, aid ):
        self.aid = aid

    def close( self ):
        with self.lock:
            self.s.close()

    def recvData( self, size, timeout = None ):
        data = None
        timeout = gevent.Timeout( timeout )
        timeout.start()
        try:
            with self.lock:
                data = ''
                while size > len( data ):
                    tmp = self.s.recv( size - len( data ) )
                    if not tmp:
                        raise DisconnectException( 'disconnect while receiving' )
                        break
                    data += tmp
        except:
            raise
        finally:
            timeout.cancel()
        return data

    def sendData( self, data, timeout = None ):
        timeout = gevent.Timeout( timeout )
        timeout.start()
        try:
            with self.lock:
                self.s.send( data )
        except:
            raise DisconnectException( 'disconnect while sending' )
        finally:
            timeout.cancel()

    def _pad( self, buffer ):
        nPad = aes_256_block_size - ( len( buffer ) % aes_256_block_size )
        if nPad == 0:
            nPad = aes_256_block_size
        return buffer + ( struct.pack( 'B', nPad ) * nPad )

    def _unpad( self, buffer ):
        nPad = struct.unpack( 'B', buffer[ -1 : ] )[ 0 ]
        if nPad <= aes_256_block_size and buffer.endswith( buffer[ -1 : ] * nPad ):
            buffer = buffer[ : 0 - nPad ]
        else:
            raise Exception( 'invalid payload padding' )
        return buffer

    def recvFrame( self, timeout = None ):
        frameSize = struct.unpack( '>I', self.recvData( 4, timeout = timeout ) )[ 0 ]
        if (1024 * 1024 * 50) < frameSize:
            raise Exception( "frame size too large: %s" % frameSize )
        frame = self.recvData( frameSize, timeout = timeout )
        frame = self._unpad( self.recvAes.update( frame ) + self.recvAes.update( '' ) )
        #frame += self.recvAes.final()
        frame = zlib.decompress( frame )
        moduleId = struct.unpack( 'B', frame[ : 1 ] )[ 0 ]
        frame = frame[ 1 : ]
        self.r.setBuffer( frame )
        messages = self.r.deserialise( isList = True )
        return ( moduleId, messages )

    def sendFrame( self, moduleId, messages, timeout = None ):
        msgList = rList()
        for msg in messages:
            msgList.addSequence( Symbols.base.MESSAGE, msg )
        hcpData = struct.pack( 'B', moduleId ) + self.r.serialise( msgList )
        data = struct.pack( '>I', len( hcpData ) )
        data += zlib.compress( hcpData )
        data = self.sendAes.update( self._pad( data ) )
        #data += self.sendAes.final()
        self.sendData( struct.pack( '>I', len( data ) ) + data, timeout = timeout )

class EndpointProcessor( Actor ):
    def init( self, parameters, resources ):
        self.handlerPortStart = parameters.get( 'handler_port_start', 10000 )
        self.handlerPortEnd = parameters.get( 'handler_port_end', 20000 )
        self.bindAddress = parameters.get( 'handler_address', ' 0.0.0.0' )
        self.privateKey = M2Crypto.RSA.load_key_string( parameters[ '_priv_key' ] )
        self.deploymentToken = parameters.get( 'deployment_token', None )
        self.enrollmentKey = parameters.get( 'enrollment_key', 'DEFAULT_HCP_ENROLLMENT_TOKEN' )

        self.r = rpcm( isHumanReadable = True )
        self.r.loadSymbols( Symbols.lookups )

        self.analyticsIntake = self.getActorHandle( resources[ 'analytics' ] )
        self.enrollmentManager = self.getActorHandle( resources[ 'enrollments' ] )
        self.stateChanges = self.getActorHandleGroup( resources[ 'states' ] )
        self.handle( 'task', self.taskClient )

        self.server = None
        self.serverPort = random.randint( self.handlerPortStart, self.handlerPortEnd )
        self.currentClients = {}
        self.moduleHandlers = { HcpModuleId.HCP : self.handlerHcp,
                                HcpModuleId.HBS : self.handlerHbs }
        self.startServer()

    def deinit( self ):
        if self.server is not None:
            self.server.close()

    def startServer( self ):
        if self.server is not None:
            self.server.close()
        while True:
            try:
                self.server = StreamServer( ( self.bindAddress, self.serverPort ), self.handleNewClient )
                self.server.start()
                self.log( 'Starting server on port %s' % self.serverPort )
                break
            except:
                self.serverPort = random.randint( self.handlerPortStart, self.handlerPortEnd )

    #==========================================================================
    # Client Handling
    #==========================================================================
    def handleNewClient( self, socket, address ):
        aid = None
        try:
            self.log( 'New connection from %s:%s' % address )
            c = _ClientContext( self, socket )
            handshake = c.recvData( rsa_2048_min_size + aes_256_iv_size, timeout = 30.0 )
            
            self.log( 'Handshake received' )
            sKey = handshake[ : rsa_2048_min_size ]
            iv = handshake[ rsa_2048_min_size : ]
            c.setKey( self.privateKey.private_decrypt( sKey, M2Crypto.RSA.pkcs1_padding ), iv )
            c.sendFrame( HcpModuleId.HCP,
                         ( rSequence().addBuffer( Symbols.base.BINARY, 
                                                  handshake ), ) )
            del( handshake )
            self.log( 'Handshake valid, getting headers' )

            moduleId, headers = c.recvFrame( timeout = 30.0 )
            if HcpModuleId.HCP != moduleId:
                raise DisconnectException( 'Headers not from expected module' )
            if headers is None:
                raise DisconnectException( 'Error deserializing headers' )
            headers = headers[ 0 ]
            self.log( 'Headers decoded, validating connection' )

            hostName = headers.get( 'base.HOST_NAME', None )
            internalIp = headers.get( 'base.IP_ADDRESS', None )
            externalIp = address[ 0 ]
            headerDeployment = headers.get( 'hcp.DEPLOYMENT_KEY', None )
            if self.deploymentToken is not None and headerDeployment != self.deploymentToken:
                raise DisconnectException( 'Sensor does not belong to this deployment' )
            aid = AgentId( headers[ 'base.HCP_ID' ] )
            if not aid.isValid or aid.isWildcarded():
                raise DisconnectException( 'Invalid sensor id: %s' % str( aid ) )
            enrollmentToken = headers.get( 'hcp.ENROLLMENT_TOKEN', None )
            if 0 == aid.unique:
                self.log( 'Sensor requires enrollment' )
                resp = self.enrollmentManager.request( 'enroll', { 'aid' : aid.invariableToString(),
                                                                   'public_ip' : externalIp,
                                                                   'internal_ip' : internalIp,
                                                                   'host_name' : hostName },
                                                       timeout = 30 )
                if not resp.isSuccess or 'aid' not in resp.data or resp.data[ 'aid' ] is None:
                    raise DisconnectException( 'Sensor could not be enrolled, come back later' )
                aid = AgentId( resp.data[ 'aid' ] )
                enrollmentToken = hashlib.md5( '%s/%s' % ( aid.invariableToString(), 
                                                           self.enrollmentKey ) ).digest()
                self.log( 'Sending sensor enrollment to %s' % aid.invariableToString() )
                c.sendFrame( HcpModuleId.HCP,
                             ( rSequence().addInt8( Symbols.base.OPERATION, 
                                                    HcpOperations.SET_HCP_ID )
                                          .addSequence( Symbols.base.HCP_ID, 
                                                        aid.toJson() )
                                          .addBuffer( Symbols.hcp.ENROLLMENT_TOKEN, 
                                                      enrollmentToken ), ) )
            else:
                expectedEnrollmentToken = hashlib.md5( '%s/%s' % ( aid.invariableToString(), 
                                                                   self.enrollmentKey ) ).digest()
                if enrollmentToken != expectedEnrollmentToken:
                    raise DisconnectException( 'Enrollment token invalid' )
            self.log( 'Valid client connection' )

            # Eventually sync the clocks at recurring intervals
            c.sendFrame( HcpModuleId.HCP, ( self.timeSyncMessage(), ) )

            c.setAid( aid )
            self.currentClients[ aid.invariableToString() ] = c
            self.stateChanges.shoot( 'live', { 'aid' : aid.invariableToString(), 
                                               'endpoint' : self.name } )

            self.log( 'Client registered, beginning to receive data' )
            while True:
                moduleId, messages = c.recvFrame( timeout = 60 * 60 )
                handler = self.moduleHandlers.get( moduleId, None )
                if handler is None:
                    self.log( 'Received data for unknown module' )
                else:
                    handler( c, messages )

        except Exception as e:
            if type( e ) is not DisconnectException:
                self.log( 'Exception while processing: %s' % str( e ) )
                raise
        finally:
            if aid is not None:
                if aid.invariableToString() in self.currentClients:
                    del( self.currentClients[ aid.invariableToString() ] )
                    self.stateChanges.shoot( 'dead', { 'aid' : aid.invariableToString(), 
                                                       'endpoint' : self.name } )
                self.log( 'Connection terminated: %s' % aid.invariableToString() )
            else:
                self.log( 'Connection terminated: %s:%s' % address )

    def handlerHcp( self, c, messages ):
        pass

    def handlerHbs( self, c, messages ):
        pass

    def timeSyncMessage( self ):
        return ( rSequence().addInt8( Symbols.base.OPERATION,
                                      HcpOperations.SET_GLOBAL_TIME )
                            .addTimestamp( Symbols.base.TIMESTAMP,
                                           int( time.time() ) ) )

    def taskClient( self, msg ):
        aid = AgentId( msg[ 'aid' ] )
        messages = msg[ 'messages' ]
        moduleId = msg[ 'module_id' ]
        c = self.currentClients.get( aid.invariableToString(), None )
        if c is not None:
            c.sendFrame( moduleId, messages, timeout = 60 * 10 )
        return ( True, )
