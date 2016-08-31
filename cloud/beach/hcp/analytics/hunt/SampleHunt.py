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
Hunt = Actor.importLib( '../../Hunts', 'Hunt' )
_xm_ = Actor.importLib( '../../utils/hcp_helpers', '_xm_' )
_x_ = Actor.importLib( '../../utils/hcp_helpers', '_x_' )

class SampleHunt ( Hunt ):
    detects = ( 'TestDetection', )

    def init( self, parameters, resources ):
        super( SampleHunt, self ).init( parameters )

    def updateHunt( self, context, newMsg ):
        if newMsg is None:
            # This is the initial detection
            self.log( 'initial detect received' )

            source = context[ 'source' ].split( ' / ' )[ 0 ]
            inv_id = context[ 'detect_id' ]
            detect = context[ 'detect' ]
            pid = _x_( detect, '?/base.PROCESS_ID' )

            self.task( source, ( ( 'mem_map', pid ), ), expiry = 60, inv_id = inv_id )
        else:
            # Detection and investigation has started
            routing, event, mtd = newMsg
            self.log( 'follow up event received' )
            fileHash = _x_( event, '*/base.HASH' )
            if fileHash is not None:
                context[ 'detect' ][ 'EvilHash' ] = fileHash.encode( 'hex' )
                self.postUpdatedDetect( context )

        # Keep this investigation alive
        return True

