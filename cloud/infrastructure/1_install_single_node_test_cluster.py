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

import os
import sys

if os.geteuid() != 0:
    print( 'Please run me as root to setup this test, but don\'t ever do that in production!' )
    sys.exit(-1)

root = os.path.join( os.path.abspath( os.path.dirname( __file__ ) ), '..', '..' )
originalDir = os.getcwd()
os.chdir( root )

def printStep( step, *ret ):
    msg = '''
===============
Step: %s
Return Values: %s
===============

''' % ( step, str( ret ) )
    print( msg )
    if any( ret ):
        print( 'Stopping execution since this step failed.' )
        sys.exit(-1)

printStep( 'Upgrade max number of file descriptors.',
           os.system( 'echo "* - nofile 1024000" >> /etc/security/limits.conf' ),
           os.system( 'echo "root - nofile 1024000" >> /etc/security/limits.conf' ),
           os.system( 'echo "session required pam_limits.so" >> /etc/pam.d/common-session' ),
           os.system( 'echo "fs.file-max = 1024000" >> /etc/sysctl.conf'),
           os.system( 'sysctl -p' ) )

printStep( 'Updating repo and upgrading existing components.',
    os.system( 'apt-get update -y' ),
    os.system( 'apt-get upgrade -y' ) )

printStep( 'Installing some basic packages required for Beach (mainly).',
    os.system( 'apt-get install python-pip python-dev debconf-utils python-m2crypto python-pexpect autoconf libtool git flex -y' ) )

printStep( 'Installing Beach.',
    os.system( 'pip install beach' ) )

printStep( 'Installing JRE for Cassandra (the hcp-scale-db)',
    os.system( 'apt-get install default-jre-headless -y' ) )

printStep( 'Installing Cassandra.',
    os.system( 'echo "deb http://debian.datastax.com/community stable main" | sudo tee -a /etc/apt/sources.list.d/cassandra.sources.list' ),
    os.system( 'curl -L http://debian.datastax.com/debian/repo_key | sudo apt-key add -' ),
    os.system( 'apt-get update -y' ) )

# Ignoring errors here because of a bug in the Ubuntu package.
os.system( 'apt-get install cassandra=2.2.3 -y' )

printStep( 'Starting Cassandra after hotfix.',
           os.system( """sed -i 's/"$JVM_PATCH_VERSION" \\\< "25"/$JVM_PATCH_VERSION -lt 25/g' /etc/cassandra/cassandra-env.sh""" ),
           os.system( 'service cassandra start' ) )

printStep( 'Initializing Cassandra schema.',
    os.system( 'sleep 10' ),
    os.system( 'cqlsh < %s' % ( os.path.join( root,
                                              'cloud',
                                              'schema',
                                              'scale_db.cql' ), ) ) )

printStep( 'Installing pip packages for various analytics components.',
    os.system( 'pip install time_uuid cassandra-driver==3.2.2 virustotal' ),
    os.system( 'pip install ipaddress' ) )

printStep( 'Installing Yara.',
    os.system( 'git clone https://github.com/refractionPOINT/yara.git' ),
    os.chdir( 'yara' ),
    os.system( './bootstrap.sh' ),
    os.system( './configure --without-crypto' ),
    os.system( 'make' ),
    os.system( 'make install' ),
    os.chdir( '..' ),
    os.system( 'git clone https://github.com/refractionPOINT/yara-python.git' ),
    os.chdir( 'yara-python' ),
    os.system( 'python setup.py build' ),
    os.system( 'python setup.py install' ),
    os.chdir( '..' ),
    os.system( 'echo "/usr/local/lib" >> /etc/ld.so.conf' ),
    os.system( 'ldconfig' ) )

printStep( 'Setting up host file entries for databases locally.',
    os.system( 'echo "127.0.0.1 hcp-state-db" >> /etc/hosts' ),
    os.system( 'echo "127.0.0.1 hcp-scale-db" >> /etc/hosts' ) )

printStep( 'Setting up the cloud tags.',
    os.system( 'python %s' % ( os.path.join( root,
                                             'tools',
                                             'update_headers.py' ), ) ) )

printStep( 'Setup LC web ui dependencies.',
    os.system( 'ln -s %s %s' % ( os.path.join( root,
                                               'cloud',
                                               'beach',
                                               'hcp',
                                               'utils',
                                               '*' ),
                                 os.path.join( root,
                                               'cloud',
                                               'limacharlie' ) ) ), )
