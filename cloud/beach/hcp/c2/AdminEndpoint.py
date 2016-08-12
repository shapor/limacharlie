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
import traceback
import hashlib
import time
rpcm = Actor.importLib( '../utils/rpcm', 'rpcm' )
rList = Actor.importLib( '../utils/rpcm', 'rList' )
rSequence = Actor.importLib( '../utils/rpcm', 'rSequence' )
AgentId = Actor.importLib( '../utils/hcp_helpers', 'AgentId' )
HbsCollectorId = Actor.importLib( '../utils/hcp_helpers', 'HbsCollectorId' )
CassDb = Actor.importLib( '../utils/hcp_databases', 'CassDb' )
CassPool = Actor.importLib( '../utils/hcp_databases', 'CassPool' )
HcpOperations = Actor.importLib( '../utils/hcp_helpers', 'HcpOperations' )
HcpModuleId = Actor.importLib( '../utils/hcp_helpers', 'HcpModuleId' )

def audited( f ):
    def wrapped( self, *args, **kwargs ):
        self.auditor.shoot( 'audit', { 'data' : args[ 0 ].data, 'cmd' : args[ 0 ].req } )
        r = f( self, *args, **kwargs )
        return r
    return wrapped

class AdminEndpoint( Actor ):
    def init( self, parameters, resources ):
        self.symbols = self.importLib( '../Symbols', 'Symbols' )()
        self._db = CassDb( parameters[ 'db' ], 'hcp_analytics', consistencyOne = True )
        self.db = CassPool( self._db,
                            rate_limit_per_sec = parameters[ 'rate_limit_per_sec' ],
                            maxConcurrent = parameters[ 'max_concurrent' ],
                            blockOnQueueSize = parameters[ 'block_on_queue_size' ] )
        self.db.start()
        self.handle( 'ping', self.ping )
        self.handle( 'hcp.get_agent_states', self.cmd_hcp_getAgentStates )
        self.handle( 'hcp.get_enrollment_rules', self.cmd_hcp_getEnrollmentRules )
        self.handle( 'hcp.add_enrollment_rule', self.cmd_hcp_addEnrollmentRule )
        self.handle( 'hcp.del_enrollment_rule', self.cmd_hcp_delEnrollmentRule )
        self.handle( 'hcp.get_taskings', self.cmd_hcp_getTaskings )
        self.handle( 'hcp.add_tasking', self.cmd_hcp_addTasking )
        self.handle( 'hcp.remove_tasking', self.cmd_hcp_delTasking )
        self.handle( 'hcp.get_modules', self.cmd_hcp_getModules )
        self.handle( 'hcp.add_module', self.cmd_hcp_addModule )
        self.handle( 'hcp.remove_module', self.cmd_hcp_delModule )
        self.handle( 'hcp.reloc_agent', self.cmd_hcp_relocAgent )
        self.handle( 'hcp.get_relocations', self.cmd_hcp_getRelocs )
        self.handle( 'hbs.set_profile', self.cmd_hbs_addProfile )
        self.handle( 'hbs.get_profiles', self.cmd_hbs_getProfiles )
        self.handle( 'hbs.del_profile', self.cmd_hbs_delProfile )
        self.handle( 'hbs.task_agent', self.cmd_hbs_taskAgent )

        self.auditor = self.getActorHandle( resources[ 'auditing' ], timeout = 5, nRetries = 3 )
        self.enrollments = self.getActorHandle( resources[ 'enrollments' ], timeout = 5, nRetries = 3 )
        self.moduleTasking = self.getActorHandle( resources[ 'module_tasking' ], timeout = 5, nRetries = 3 )

    def deinit( self ):
        pass

    def ping( self, msg ):
        return ( True, { 'pong' : time.time() } )

    @audited
    def cmd_hcp_getAgentStates( self, msg ):
        request = msg.data
        hostName = request.get( 'hostname', None )
        aids = []
        if 'agent_id' in request:
            aids.append( AgentId( request[ 'agent_id' ] ) )
        elif hostName is not None:
            aids = [ AgentId( x ) for x in self.db.getOne( 'SELECT aid FROM sensor_hostnames WHERE hostname = %s', hostName ) ]
        else:
            aids = None

        data = { 'agents' : {} }

        if aids is None:
            for row in self.db.execute( 'SELECT org, subnet, unique, platform, enroll, alive, dead, hostname, ext_ip, int_ip FROM sensor_states' ):
                    tmpAid = AgentId( ( row[ 0 ], row[ 1 ], row[ 2 ], row[ 3 ] ) )
                    tmpData = {}
                    tmpData[ 'agent_id' ] = str( tmpAid )
                    tmpData[ 'last_external_ip' ] = row[ 8 ]
                    tmpData[ 'last_internal_ip' ] = row[ 9 ]
                    tmpData[ 'last_hostname' ] = row[ 7 ]
                    data[ 'agents' ][ str( tmpAid ) ] = tmpData
        elif 0 != len( aids ):
            for aid in aids:
                filt = aid.isWhere( isSimpleOnly = False )
                for row in self.db.execute( 'SELECT org, subnet, unique, platform, enroll, alive, dead, hostname, ext_ip, int_ip FROM sensor_states WHERE %s' % filt[ 0 ], filt[ 1 ] ):
                    tmpAid = AgentId( ( row[ 0 ], row[ 1 ], row[ 2 ], row[ 3 ] ) )
                    tmpData = {}
                    tmpData[ 'agent_id' ] = str( tmpAid )
                    tmpData[ 'last_external_ip' ] = row[ 8 ]
                    tmpData[ 'last_internal_ip' ] = row[ 9 ]
                    tmpData[ 'last_hostname' ] = row[ 7 ]
                    data[ 'agents' ][ str( tmpAid ) ] = tmpData
        
        return ( True, data )

    @audited
    def cmd_hcp_getEnrollmentRules( self, msg ):
        rules = []
        data = { 'rules' : rules }
        for row in self.db.execute( 'SELECT aid, ext_ip, int_ip, hostname, new_org, new_subnet FROM enrollment' ):
            rules.append( { 'mask' : AgentId( row[ 0 ] ),
                            'external_ip' : row[ 1 ],
                            'internal_ip' : row[ 2 ],
                            'hostname' : row[ 3 ],
                            'new_org' : row[ 4 ],
                            'new_subnet' : row[ 5 ] } )

        return ( True, data )

    @audited
    def cmd_hcp_addEnrollmentRule( self, msg ):
        request = msg.data
        self.db.execute( 'INSERT INTO enrollment ( aid, ext_ip, int_ip, hostname, new_org, new_subnet ) VALUES ( %s, %s, %s, %s, %s, %s )',
                         ( str( AgentId( request[ 'mask' ] ) ), 
                           request[ 'external_ip' ],
                           request[ 'internal_ip' ],
                           request[ 'hostname' ],
                           request[ 'new_org' ],
                           request[ 'new_subnet' ] ) )

        self.delay( 5, self.enrollments.broadcast, 'reload', {} )

        return ( True, )

    @audited
    def cmd_hcp_delEnrollmentRule( self, msg ):
        request = msg.data
        mask = AgentId( request[ 'mask' ] ).asString()
        e_ip = request[ 'external_ip' ]
        i_ip = request[ 'internal_ip' ]
        hostname = request[ 'hostname' ]

        self.db.execute( 'DELETE FROM enrollment WHERE aid = %s AND ext_ip = %s AND int_ip = %s AND hostname = %s',
                         ( mask, e_ip, i_ip, hostname ) )

        self.delay( 5, self.enrollments.broadcast, 'reload', {} )

        return ( True, )

    @audited
    def cmd_hcp_getTaskings( self, msg ):
        data = {}
        data[ 'taskings' ] = []
        for row in self.db.execute( 'SELECT aid, mid, mhash FROM hcp_module_tasking' ):
            data[ 'taskings' ].append( { 'mask' : AgentId( row[ 0 ] ),
                                                 'module_id' : row[ 1 ],
                                                 'hash' : row[ 2 ] } )
        return ( True, data )

    @audited
    def cmd_hcp_addTasking( self, msg ):
        request = msg.data
        mask = AgentId( request[ 'mask' ] ).asString()
        moduleid = int( request[ 'module_id' ] )
        h = str( request[ 'hash' ] )
        self.db.execute( 'INSERT INTO hcp_module_tasking ( aid, mid, mhash ) VALUES ( %s, %s, %s )',
                         ( mask, moduleid, h ) )

        self.delay( 5, self.moduleTasking.broadcast, 'reload', {} )

        return ( True, )

    @audited
    def cmd_hcp_delTasking( self, msg ):
        request = msg.data
        mask = AgentId( request[ 'mask' ] ).asString()
        moduleid = int( request[ 'module_id' ] )
        h = str( request[ 'hash' ] )
        self.db.execute( 'DELETE FROM hcp_module_tasking WHERE aid = %s AND mid = %s AND mhash = %s',
                         ( mask, moduleid, h ) )

        self.delay( 5, self.moduleTasking.broadcast, 'reload', {} )
        
        return ( True, )

    @audited
    def cmd_hcp_getModules( self, msg ):
        modules = []
        data = { 'modules' : modules }
        for row in self.db.execute( 'SELECT mid, mhash, description FROM hcp_modules' ):
            modules.append( { 'module_id' : row[ 0 ],
                              'hash' : row[ 1 ],
                              'description' : row[ 2 ] } )

        return ( True, data )

    @audited
    def cmd_hcp_addModule( self, msg ):
        request = msg.data
        moduleid = int( request[ 'module_id' ] )
        h = str( request[ 'hash' ] )
        b = request[ 'bin' ]
        sig = request[ 'signature' ]
        description = ''
        if 'description' in request:
            description = request[ 'description' ]
        self.db.execute( 'INSERT INTO hcp_modules ( mid, mhash, mdat, msig, description ) VALUES ( %s, %s, %s, %s, %s )',
                         ( moduleid, h, bytearray( b ), bytearray( sig ), description ) )

        data = {}
        data[ 'hash' ] = h
        data[ 'module_id' ] = moduleid
        data[ 'description' ] = description

        return ( True, data )

    @audited
    def cmd_hcp_delModule( self, msg ):
        request = msg.data
        moduleid = int( request[ 'module_id' ] )
        h = str( request[ 'hash' ] )

        self.db.execute( 'DELETE FROM hcp_modules WHERE mid = %s AND mhash = %s',
                         ( moduleid, h ) )

        return ( True, )

    @audited
    def cmd_hcp_relocAgent( self, msg ):
        request = msg.data
        fromAgent = AgentId( request[ 'agentid' ] ).asString()
        newOrg = request[ 'new_org' ]
        newSub = request[ 'new_subnet' ]

        self.db.execute( 'INSERT INTO sensor_reloc ( aid, new_org, new_subnet ) VALUES ( %s, %s, %s )',
                         ( fromAgent, newOrg, newSub ) )
        
        return ( True, )

    @audited
    def cmd_hcp_getRelocs( self, msg ):
        data = { 'relocations' : {} }
        for row in self.db.execute( 'SELECT aid, new_org, new_subnet FROM sensor_reloc' ):
            data[ 'relocations' ][ AgentId( row[ 0 ] ) ] = { 'agentid' :AgentId( row[ 0 ] ),
                                                             'new_org' : row[ 1 ],
                                                             'new_subnet' : row[ 2 ] }
        
        return ( True, data )

    @audited
    def cmd_hbs_getProfiles( self, msg ):
        data = { 'profiles' : [] }
        for row in self.db.execute( 'SELECT aid, oprofile FROM hbs_profiles' ):
            data[ 'profiles' ].append( { 'mask' : row[ 0 ],
                                         'original_configs' : row[ 1 ] } )

        return ( True, data )

    @audited
    def cmd_hbs_addProfile( self, msg ):
        request = msg.data
        mask = AgentId( request[ 'mask' ] ).asString()
        c = request[ 'module_configs' ]
        isValidConfig = False
        profileError = ''
        oc = c
        configHash = None

        if c is not None and '' != c:
            r = rpcm( isDebug = True )
            rpcm_environment = { '_' : self.symbols,
                                 'rList' : rList,
                                 'rSequence' : rSequence,
                                 'HbsCollectorId' : HbsCollectorId }
            try:
                profile = eval( c.replace( '\n', '' ), rpcm_environment )
            except:
                profile = None
                profileError = traceback.format_exc()

            if profile is not None:
                if type( profile ) is rList:
                    profile = r.serialise( profile )

                    if profile is not None:
                        isValidConfig = True
                        c = profile
                        configHash = hashlib.sha256( profile ).hexdigest()
                    else:
                        profileError = 'config could not be serialised'
                else:
                    profileError = 'config did not evaluate as an rList: %s' % type( profile )

        else:
            isValidConfig = True

        if isValidConfig:
            self.db.execute( 'INSERT INTO hbs_profiles ( aid, cprofile, oprofile, hprofile ) VALUES ( %s, %s, %s, %s )',
                             ( mask, bytearray( c ), oc, configHash ) )
            response = ( True, )
        else:
            response = ( False, profileError )

        return response

    @audited
    def cmd_hbs_delProfile( self, msg ):
        request = msg.data
        mask = AgentId( request[ 'mask' ] ).asString()

        self.db.execute( 'DELETE FROM hbs_profiles WHERE aid = %s',
                         ( mask, ) )

        return ( True, )

    @audited
    def cmd_hbs_taskAgent( self, msg ):
        request = msg.data
        agent = AgentId( request[ 'agentid' ] ).asString()
        task = request[ 'task' ]

        self.db.execute( 'INSERT INTO hbs_queue ( aid, task ) VALUES ( %s, %s )',
                         ( agent, bytearray( task ) ) )
        
        return ( True, )