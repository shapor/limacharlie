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
ObjectTypes = Actor.importLib( '../../utils/ObjectsDb', 'ObjectTypes' )
ObjectKey = Actor.importLib( '../../utils/ObjectsDb', 'ObjectKey' )
StatelessActor = Actor.importLib( '../../Detects', 'StatelessActor' )
RingCache = Actor.importLib( '../../utils/hcp_helpers', 'RingCache' )

class KnownObjects ( StatelessActor ):
    def init( self, parameters, resources ):
        super( KnownObjects, self ).init( parameters, resources )

        self.known = {}
        self.infoCache = RingCache( maxEntries = 100, isAutoAdd = False )

        self.source_refresh_sec = parameters.get( 'source_refresh_sec', 3600 )
        self.source_cat = parameters.get( 'source', 'sources/known_objects/' )

        self.source = self.getActorHandle( self.source_cat, nRetries = 3, timeout = 10 )

        self.schedule( self.source_refresh_sec, self.refreshSource )

    def refreshSource( self ):
        data = self.source.request( 'get_known' )
        if data.isSuccess:
            self.known = data.data.get( 'k', {} )
            self.log( 'fetched %s known objects' % len( self.known ) )
        else:
            self.logCritical( 'could not fetch known objects from source' )

    def _getObjectInfo( self, k ):
        if k in self.infoCache:
            info = self.infoCache.get( k )
        else:
            info = self.source.request( 'get_info', { 'k' : k } )
            if info.isSuccess:
                info = info.data
                if 0 != len( info ):
                    self.infoCache.add( k, info )
            else:
                info = {}
        return info

    def process( self, detects, msg ):
        routing, event, mtd = msg.data
        
        for oType, objects in mtd[ 'obj' ].iteritems():
            for o in objects:
                k = ObjectKey( o, oType )
                if k in self.known:
                    detects.add( 99, 'known bad object found', { 'otype' : oType, 'o' : o, 'info' : self._getObjectInfo( k ) } )
