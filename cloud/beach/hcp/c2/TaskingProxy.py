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
import ipaddress
CassDb = Actor.importLib( '../utils/hcp_databases', 'CassDb' )
CassPool = Actor.importLib( '../utils/hcp_databases', 'CassPool' )
rpcm = Actor.importLib( '../utils/rpcm', 'rpcm' )
rList = Actor.importLib( '../utils/rpcm', 'rList' )
rSequence = Actor.importLib( '../utils/rpcm', 'rSequence' )
AgentId = Actor.importLib( '../utils/hcp_helpers', 'AgentId' )

class TaskingProxy( Actor ):
    def init( self, parameters, resources ):
        self.handle( 'task', self.task )

    def deinit( self ):
        pass

    def task( self, msg ):
        return ( True, )
