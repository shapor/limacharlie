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

REPO_ROOT = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), '..', '..' )

if 1 < len( sys.argv ):
    BEACH_CONFIG_FILE = os.path.abspath( sys.argv[ 1 ] )
else:
    BEACH_CONFIG_FILE = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), 'sample_cluster.yaml' )

SCALE_DB = [ 'hcp-scale-db' ]
STATE_DB = { 'url' : 'hcp-state-db',
             'db' : 'hcp',
             'user' : 'root',
             'password' : 'letmein' }

#######################################
# EnrollmentManager
# This actor is responsible for managing
# enrollment requests from sensors.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'EnrollmentManager',
        initialInstances = 1,
        maxInstances = 1,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/EnrollmentManager',
                      'c2/enrollments/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'enrollment/a3bebbb0-00e2-4345-990b-4c36a40b475e',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
                                'admin/dde768a4-8f27-4839-9e26-354066c8540e' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# StateUpdater
# This actor is responsible for updating
# the current status of connections with
# sensors.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'StateUpdater',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/StateUpdater',
                      [ 'c2/stateupdater/1.0',
                        'c2/states/updater/1.0' ] ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'stateupdater/d3c521c6-d5c6-4726-9b0c-84d0ac356409',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# PersistentTasking
# This actor is responsible for updating
# the current status of connections with
# sensors.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'PersistentTasking',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/PersistentTasking',
                      [ 'c2/persistenttasking/1.0',
                        'c2/states/persistenttasking/1.0' ] ),
        actorKwArgs = {
            'resources' : { 'tasking_proxy' : 'c2/taskingproxy/' },
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'persistenttasking/54158388-2b0b-47c0-9642-f90835b5057b',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
                                'admin/dde768a4-8f27-4839-9e26-354066c8540e' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# SensorDirectory
# This actor is responsible for keeping
# a list of which sensors are online and
# at which endpoint.
# Parameters:
#######################################
Patrol( 'SensorDirectory',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'c2/SensorDirectory',
                      [ 'c2/sensordir/1.0',
                        'c2/states/sensordir/1.0' ] ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : {},
            'secretIdent' : 'sensordir/3babff24-400b-4233-bcac-18f538a88fe1',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
                                'taskingproxy/794729aa-1ef5-4930-b377-48dda7b759a5' ],
            'n_concurrent' : 5,
            'isIsolated' : False } )

#######################################
# TaskingProxy
# This actor is responsible for proxying
# various taskings from actors in the
# cloud to the relevant endpoint and sensors.
# Parameters:
#######################################
Patrol( 'TaskingProxy',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/TaskingProxy',
                      [ 'c2/taskingproxy/1.0' ] ),
        actorKwArgs = {
            'resources' : { 'sensor_dir' : 'c2/sensordir/' },
            'parameters' : {},
            'secretIdent' : 'taskingproxy/794729aa-1ef5-4930-b377-48dda7b759a5',
            'trustedIdents' : [ 'autotasking/a6cd8d9a-a90c-42ec-bd60-0519b6fb1f64',
                                'admin/dde768a4-8f27-4839-9e26-354066c8540e',
                                'persistenttasking/54158388-2b0b-47c0-9642-f90835b5057b' ],
            'n_concurrent' : 5,
            'isIsolated' : False } )

#######################################
# ModuleManager
# This actor is responsible for syncing
# with sensors and keeping their loaded
# modules up to date.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'ModuleManager',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/ModuleManager',
                      [ 'c2/modulemanager/1.0' ] ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'modulemanager/1ecf1cd3-044d-434d-9134-b9b2c976ccad',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
                                'admin/dde768a4-8f27-4839-9e26-354066c8540e' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# AdminEndpoint
# This actor will serve as a comms
# endpoint by the admin_lib/cli
# to administer the LC.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'AdminEndpoint',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        scalingFactor = 5000,
        actorArgs = ( 'c2/AdminEndpoint',
                      'c2/admin/1.0' ),
        actorKwArgs = {
            'resources' : { 'auditing' : 'c2/auditing',
                            'enrollments' : 'c2/enrollments',
                            'module_tasking' : 'c2/modulemanager',
                            'hbs_profiles' : 'c2/hbsprofilemanager',
                            'tasking_proxy' : 'c2/taskingproxy/',
                            'persistent_tasks' : 'c2/persistenttasking/' },
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'admin/dde768a4-8f27-4839-9e26-354066c8540e',
            'trustedIdents' : [ 'cli/955f6e63-9119-4ba6-a969-84b38bfbcc05' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# HbsProfileManager
# This actor is responsible for syncing
# with sensors to keep HBS profiles up
# to date.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'HbsProfileManager',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/HbsProfileManager',
                      [ 'c2/hbsprofilemanager/1.0' ] ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 100 },
            'secretIdent' : 'hbsprofilemanager/8326405a-0698-4a91-9b30-d4ef9e4b9926',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
                                'admin/dde768a4-8f27-4839-9e26-354066c8540e' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# EndpointProcessor
# This actor will process incoming
# connections from the sensors.
# Parameters:
# deployment_key: The deployment key
#    to enforce if needed, it helps
#    to filter out sensors beaconing
#    to you that are not related to
#    your deployment.
# _priv_key: the C2 private key.
# handler_port_*: start and end port
#    where incoming connections will
#    be processed.
# enrollment_token: secret token used
#    to verify enrolled sensor identities.
#######################################
Patrol( 'EndpointProcessor',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'c2/EndpointProcessor',
                      'c2/endpoint/1.0' ),
        actorKwArgs = {
            'resources' : { 'analytics' : 'analytics/intake',
                            'enrollments' : 'c2/enrollments',
                            'states' : 'c2/states/',
                            'module_tasking' : 'c2/modulemanager',
                            'hbs_profiles' : 'c2/hbsprofilemanager' },
            'parameters' : { 'deployment_key' : None,
                             'handler_port_start' : 80,
                             'handler_port_end' : 80,
                             'enrollment_token' : 'DEFAULT_HCP_ENROLLMENT_TOKEN',
                             '_priv_key' : open( os.path.join( REPO_ROOT,
                                                               'keys',
                                                               'c2.priv.pem' ), 'r' ).read() },
            'secretIdent' : 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd',
            'trustedIdents' : [ 'taskingproxy/794729aa-1ef5-4930-b377-48dda7b759a5' ],
            'n_concurrent' : 5,
            'isIsolated' : False } )

###############################################################################
# Analysis Intake
###############################################################################

#######################################
# AnalyticsIntake
# This actor receives the messages from
# the beacons and does initial parsing
# of components that will be of
# interest to all analytics and then
# forwards it on to other components.
#######################################
Patrol( 'AnalyticsIntake',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/AnalyticsIntake',
                      'analytics/intake/1.0' ),
        actorKwArgs = {
            'resources' : { 'stateless' : 'analytics/stateless/intake',
                            'stateful' : 'analytics/stateful/intake',
                            'modeling' : 'analytics/modeling/intake',
                            'investigation' : 'analytics/investigation/intake',
                            'relation_builder' : 'analytics/async/relbuilder' },
            'parameters' : {},
            'secretIdent' : 'intake/6058e556-a102-4e51-918e-d36d6d1823db',
            'trustedIdents' : [ 'beacon/09ba97ab-5557-4030-9db0-1dbe7f2b9cfd' ],
            'n_concurrent' : 5 } )

#######################################
# AnalyticsModeling
# This actor is responsible to model
# and record the information extracted
# from the messages in all the different
# pre-pivoted databases.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'AnalyticsModeling',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/AnalyticsModeling',
                      'analytics/modeling/intake/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 200000,
                             'retention_raw_events' : ( 60 * 60 * 24 * 14 ),
                             'retention_investigations' : ( 60 * 60 * 24 * 30 ),
                             'retention_objects_primary' : ( 60 * 60 * 24 * 365 ),
                             'retention_objects_secondary' : ( 60 * 60 * 24 * 30 * 6 ),
                             'retention_explorer' : ( 60 * 60 * 24 * 30 ) },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'intake/6058e556-a102-4e51-918e-d36d6d1823db' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# AnalyticsStateless
# This actor responsible for sending
# messages of the right type to the
# right stateless detection actors.
#######################################
Patrol( 'AnalyticsStateless',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 2000,
        actorArgs = ( 'analytics/AnalyticsStateless',
                      'analytics/stateless/intake/1.0' ),
        actorKwArgs = {
            'resources' : { 'all' : 'analytics/stateless/all/',
                            'output' : 'analytics/output/events/',
                            'specific' : 'analytics/stateless/%s/%s/' },
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'intake/6058e556-a102-4e51-918e-d36d6d1823db' ],
            'n_concurrent' : 5 } )

#######################################
# AnalyticsStateful
# This actor responsible for sending
# messages of the right type to the
# right stateful detection actors.
#######################################
Patrol( 'AnalyticsStateful',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/AnalyticsStateful',
                      'analytics/stateful/intake/1.0' ),
        actorKwArgs = {
            'resources' : { 'modules' : 'analytics/stateful/modules/%s/' },
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'intake/6058e556-a102-4e51-918e-d36d6d1823db' ],
            'n_concurrent' : 5 } )

#######################################
# AsynchronousRelationBuilder
# This actor responsible for sending
# messages of the right type to the
# right stateful detection actors.
#######################################
Patrol( 'AsynchronousRelationBuilder',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/AsynchronousRelationBuilder',
                      'analytics/async/relbuilder/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 200,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 200000 },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'intake/6058e556-a102-4e51-918e-d36d6d1823db' ],
            'n_concurrent' : 5 } )

#######################################
# AnalyticsReporting
# This actor receives Detecs from the
# stateless and stateful detection
# actors and ingest them into the
# reporting pipeline.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
# paging_dest: email addresses to page.
#######################################
Patrol( 'AnalyticsReporting',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/AnalyticsReporting',
                      'analytics/reporting/1.0' ),
        actorKwArgs = {
            'resources' : { 'output' : 'analytics/output/detects',
                            'paging' : 'paging' },
            'parameters' : { 'db' : SCALE_DB,
                             'rate_limit_per_sec' : 10,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 200000,
                             'paging_dest' : [] },
            'secretIdent' : 'reporting/9ddcc95e-274b-4a49-a003-c952d12049b8',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
                                'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# CEFDetectsOutput
# This actor receives Detecs from the
# reporting actor and outputs them to
# a CEF-based SIEM.
# Parameters:
# siem_server: the log destination.
# lc_web: the base url for the LC GUI.
# scale_db: connection information to
#   Cassandra scale database.
# beach_config: the path to the beach
#   config file.
#######################################
Patrol( 'CEFOutput',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/CEFDetectsOutput',
                      'analytics/output/detects/cef/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'siem_server' : '/dev/log',
                             'lc_web' : '127.0.0.1',
                             'scale_db' : SCALE_DB,
                             'beach_config' : BEACH_CONFIG_FILE },
            'secretIdent' : 'output/bf73a858-8f05-45ab-9ead-05493e29429a',
            'trustedIdents' : [ 'reporting/9ddcc95e-274b-4a49-a003-c952d12049b8' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# FileEventsOutput
# This actor writes out all events as
# files to the disk for ingestion in
# other systems like Splunk.
# Parameters:
# output_dir: the directory where
#   events get written to.
# max_bytes: max size of single log
#   file before being rotated.
# backup_count: number of rotated 
#   files to keep.
# is_flat: set to True to format events
#   into flat key/value records on 
#   systems that don't support nesting
#   like LogStash
#######################################
Patrol( 'FileEventsOutput',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/FileEventsOutput',
                      'analytics/output/events/file/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'output_dir' : '/tmp/lc_out/',
                             'is_flat' : False },
            'secretIdent' : 'output/bf73a858-8f05-45ab-9ead-05493e29429a',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5,
            'isIsolated' : False } )

#######################################
# AnalyticsInvestigation
# This actor responsible for sending
# messages to the actors interested in
# specific investigations.
# Parameters:
# ttl: the number of seconds the data
#    flow for an investigation remains
#    open after last data seen.
#######################################
Patrol( 'AnalyticsInvestigation',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/AnalyticsInvestigation',
                      'analytics/investigation/intake/1.0' ),
        actorKwArgs = {
            'resources' : { 'investigations' : 'analytics/inv_id/%s' },
            'parameters' : { 'ttl' : ( 60 * 60 * 24 ) },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'intake/6058e556-a102-4e51-918e-d36d6d1823db' ],
            'n_concurrent' : 5 } )

#######################################
# ModelView
# This actor is responsible to query
# the model to retrieve different
# advanced queries for UI or for
# other detection mechanisms.
# Parameters:
# db: the Cassandra seed nodes to
#    connect to for storage.
# rate_limit_per_sec: number of db ops
#    per second, limiting to avoid
#    db overload since C* is bad at that.
# max_concurrent: number of concurrent
#    db queries.
# block_on_queue_size: stop queuing after
#    n number of items awaiting ingestion.
#######################################
Patrol( 'AnalyticsModelView',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/ModelView',
                      'models/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'scale_db' : SCALE_DB,
                             'state_db' : STATE_DB,
                             'rate_limit_per_sec' : 500,
                             'max_concurrent' : 10,
                             'beach_config' : BEACH_CONFIG_FILE },
            'trustedIdents' : [ 'lc/0bf01f7e-62bd-4cc4-9fec-4c52e82eb903',
                                'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517',
                                'rest/be41bb0f-449a-45e9-87d8-ef4533336a2d' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

#######################################
# AutoTasking
# This actor receives tasking requests
# from other Actors (detection Actors
# for now), applies a QoS and tasks.
# Parameters:
# _hbs_key: the private HBS key to task.
# beach_config: the path to the beach
#    config file.
# sensor_qph: the maximum number of
#    taskings per hour per sensor.
# global_qph: the maximum number of
#    tasking per hour globally.
# allowed: the list of CLI commands
#    that can be tasked.
#######################################
Patrol( 'AutoTasking',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/AutoTasking',
                      'analytics/autotasking/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { '_hbs_key' : open( os.path.join( REPO_ROOT,
                                                              'keys',
                                                              'hbs_root.priv.der' ), 'r' ).read(),
                             'beach_config' : BEACH_CONFIG_FILE,
                             'sensor_qph' : 100,
                             'global_qph' : 1000,
                             'allowed' : [ 'file_info',
                                           'file_hash',
                                           'mem_map',
                                           'mem_strings',
                                           'mem_handles',
                                           'os_processes',
                                           'hidden_module_scan',
                                           'exec_oob_scan',
                                           'history_dump',
                                           'remain_live',
                                           'exfil_add',
                                           'critical_add',
                                           'hollowed_module_scan',
                                           'os_services',
                                           'os_drivers',
                                           'os_autoruns',
                                           'yara_update' ],
                             'log_file' : './admin_cli.log' },
            'secretIdent' : 'autotasking/a6cd8d9a-a90c-42ec-bd60-0519b6fb1f64',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
                                'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517' ],
            'n_concurrent' : 5 } )

#######################################
# HuntsManager
# This actor manages the registration
# and configuration of the various
# automated hunts.
# Parameters:
# beach_config: the path to the beach
#    config file.
#######################################
Patrol( 'HuntsManager',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/HuntsManager',
                      'analytics/huntsmanager/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'beach_config' : BEACH_CONFIG_FILE },
            'secretIdent' : 'huntsmanager/d666cbc3-38d5-4086-b9ce-c543625ee45c',
            'trustedIdents' : [ 'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517' ],
            'n_concurrent' : 5 } )

#######################################
# PagingActor
# This actor responsible for sending
# pages by email.
# Parameters:
# from: email/user to send page from.
# password: password of the account
#    used to send.
# smtp_server: URI of the smtp server.
# smtp_port: port of the smtp server.
#######################################
Patrol( 'PagingActor',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'PagingActor',
                      'paging/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : {},
            'secretIdent' : 'paging/31d29b6a-d455-4df7-a196-aec3104f105d',
            'trustedIdents' : [ 'reporting/9ddcc95e-274b-4a49-a003-c952d12049b8' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/VirusTotalActor
# This actor retrieves VT reports while
# caching results.
# Parameters:
# _key: the VT API Key.
# qpm: maximum number of queries to
#    to VT per minute, based on your
#    subscription level, default of 4
#    which matches their free tier.
# cache_size: how many results to cache.
#######################################
Patrol( 'VirusTotalActor',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 2000,
        actorArgs = ( 'analytics/VirusTotalActor',
                      'analytics/virustotal/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'qpm' : 4 },
            'secretIdent' : 'virustotal/697bfbf7-aa78-41f3-adb8-26f59bdba0da',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
                                'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517' ],
            'n_concurrent' : 1 } )

#######################################
# StatsComputer
# This actor computes stats on Objects
# and their relationships to determine
# which ones can be used as strong
# outliers for runtime detection.
# Parameters:
# scale_db: the Cassandra seed nodes to
#    connect to for storage.
# beach_config: path to the beach config.
#######################################
Patrol( 'StatsComputer',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 100000,
        actorArgs = ( 'analytics/StatsComputer',
                      'analytics/stats/1.0' ),
        actorKwArgs = {
            'resources' : {},
            'parameters' : { 'scale_db' : SCALE_DB,
                             'beach_config' : BEACH_CONFIG_FILE },
            'secretIdent' : 'stats/3088dc10-b40c-40f8-bf3a-d07be4758098',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
                                'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

###############################################################################
# Stateless Detection
###############################################################################

#######################################
# stateless/TestDetection
# This actor simply looks for a
# file_path containing the string
# 'hcp_evil_detection_test' and generates
# a detect and a file_hash tasking for it.
#######################################
Patrol( 'TestDetection',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/TestDetection',
                      'analytics/stateless/common/notification.NEW_PROCESS/testdetection/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/ActiveDirectoryReference
# This actor looks for execution with a
# command line referencing the AD DB.
#######################################
Patrol( 'ActiveDirectoryReference',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/ActiveDirectoryReference',
                      [ 'analytics/stateless/windows/notification.NEW_PROCESS/adreference/1.0' ] ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/WinSuspExecLoc
# This actor looks for execution from
# various known suspicious locations.
#######################################
Patrol( 'WinSuspExecLoc',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/WinSuspExecLoc',
                      [ 'analytics/stateless/windows/notification.NEW_PROCESS/suspexecloc/1.0',
                        'analytics/stateless/windows/notification.CODE_IDENTITY/suspexecloc/1.0' ] ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/WinSuspExecName
# This actor looks for execution from
# executables with suspicious names that
# try to hide the fact the files are
# executables.
#######################################
Patrol( 'WinSuspExecName',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/WinSuspExecName',
                      [ 'analytics/stateless/windows/notification.NEW_PROCESS/suspexecname/1.0',
                        'analytics/stateless/windows/notification.CODE_IDENTITY/suspexecname/1.0' ] ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/MacSuspExecLoc
# This actor looks for execution from
# various known suspicious locations.
#######################################
Patrol( 'MacSuspExecLoc',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/MacSuspExecLoc',
                      [ 'analytics/stateless/osx/notification.NEW_PROCESS/suspexecloc/1.0',
                        'analytics/stateless/osx/notification.CODE_IDENTITY/suspexecloc/1.0' ] ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/BatchSelfDelete
# This actor looks for patterns of an
# executable deleteing itself using
# a batch script.
#######################################
Patrol( 'BatchSelfDelete',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/BatchSelfDelete',
                      'analytics/stateless/windows/notification.NEW_PROCESS/batchselfdelete/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/KnownObjects
# This actor looks for known Objects
# in all messages. It receives those
# known Objects from another actor
# source that can be customized.
# Parameters:
# source: the beach category to query
#    to receive the known Objects.
# source_refresh_sec: how often to
#    refresh its known Objects from
#    the source.
#######################################
Patrol( 'KnownObjects',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/KnownObjects',
                      [ 'analytics/stateless/common/notification.NEW_PROCESS/knownobjects/1.0',
                        'analytics/stateless/common/notification.CODE_IDENTITY/knownobjects/1.0',
                        'analytics/stateless/common/notification.OS_SERVICES_REP/knownobjects/1.0',
                        'analytics/stateless/common/notification.OS_DRIVERS_REP/knownobjects/1.0',
                        'analytics/stateless/common/notification.OS_AUTORUNS_REP/knownobjects/1.0',
                        'analytics/stateless/common/notification.DNS_REQUEST/knownobjects/1.0' ] ),
        actorKwArgs = {
            'parameters' : { 'source' : 'sources/known_objects/',
                             'source_refresh_sec' : 3600 },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/VirusTotalKnownBad
# This actor checks all hashes against
# VirusTotal and reports hashes that
# have more than a threshold of AV
# reports, while caching results.
# Parameters:
# _key: the VT API Key.
# min_av: minimum number of AV reporting
#    a result on the hash before it is
#    reported as a detection.
#######################################
Patrol( 'VirusTotalKnownBad',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 2000,
        actorArgs = ( 'analytics/stateless/VirusTotalKnownBad',
                      [ 'analytics/stateless/common/notification.CODE_IDENTITY/virustotalknownbad/1.0',
                        'analytics/stateless/common/notification.OS_SERVICES_REP/virustotalknownbad/1.0',
                        'analytics/stateless/common/notification.OS_DRIVERS_REP/virustotalknownbad/1.0',
                        'analytics/stateless/common/notification.OS_AUTORUNS_REP/virustotalknownbad/1.0' ] ),
        actorKwArgs = {
            'parameters' : { 'qpm' : 1 },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 2 } )

#######################################
# stateless/WinFirewallCliMods
# This actor looks for patterns of an
# executable adding firewall rules
# via a command line interface.
#######################################
Patrol( 'WinFirewallCliMods',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/WinFirewallCliMods',
                      'analytics/stateless/windows/notification.NEW_PROCESS/firewallclimods/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/HiddenModules
# This actor looks hidden module
# notifications.
#######################################
Patrol( 'HiddenModules',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/HiddenModules',
                      'analytics/stateless/common/notification.HIDDEN_MODULE_DETECTED/hiddenmodules/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/WinOobExec
# This actor looks OOB execution
# notifications.
#######################################
Patrol( 'WinOobExec',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 5000,
        actorArgs = ( 'analytics/stateless/WinOobExec',
                      'analytics/stateless/windows/notification.EXEC_OOB/oobexec/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/ExecNotOnDisk
# This actor for code loading from disk
# but not visible on disk. In other
# words it has a code ident but no hash.
#######################################
Patrol( 'ExecNotOnDisk',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/ExecNotOnDisk',
                      'analytics/stateless/common/notification.CODE_IDENTITY/execnotondisk/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/HollowedProcess
# This actor for mismatch between a
# module on disk and in memory for
# signs of process hollowing.
#######################################
Patrol( 'HollowedProcess',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/stateless/HollowedProcess',
                      [ 'analytics/stateless/windows/notification.MODULE_MEM_DISK_MISMATCH/hollowedprocess/1.0',
                        'analytics/stateless/linux/notification.MODULE_MEM_DISK_MISMATCH/hollowedprocess/1.0' ] ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/YaraDetects
# This actor generates detects from
# sensor events with Yara detections.
#######################################
Patrol( 'YaraDetects',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/stateless/YaraDetects',
                      'analytics/stateless/common/notification.YARA_DETECTION/yaradetects/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/YaraUpdater
# This actor does not generate detects,
# it merely updates new sensor coming
# online with the most recent Yara rules.
#######################################
Patrol( 'YaraUpdater',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/stateless/YaraUpdater',
                      'analytics/stateless/common/notification.STARTING_UP/yaraupdater/1.0' ),
        actorKwArgs = {
            'parameters' : { 'rules_dir' : 'hcp/analytics/yara_rules/',
                             'remote_rules' : { 'windows/yararules.com.yar' : 'http://yararules.com/rules/malware.yar' } },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateless/NewObjects
# This actor looks for new objects of
# specifically interesting types.
#######################################
Patrol( 'NewObjects',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 1000,
        actorArgs = ( 'analytics/stateless/NewObjects',
                      'analytics/stateless/all/newobjects/1.0' ),
        actorKwArgs = {
            'parameters' : { 'types' : [ 'SERVICE_NAME', 'AUTORUNS' ],
                             'db' : SCALE_DB,
                             'rate_limit_per_sec' : 10,
                             'max_concurrent' : 5,
                             'block_on_queue_size' : 200000 },
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5,
            'isIsolated' : True } )

###############################################################################
# Stateful Detection
###############################################################################
#######################################
# stateful/WinDocumentExploit
# This actor looks for various stateful
# patterns indicating documents being
# exploited.
#######################################
Patrol( 'WinDocumentExploit',
        initialInstances = 2,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/stateful/WinDocumentExploit',
                      'analytics/stateful/modules/windows/documentexploit/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateful/SensorIssues
# This actor looks for issues with the
# sensor.
#######################################
Patrol( 'SensorIssues',
        initialInstances = 2,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/stateful/SensorIssues',
                      'analytics/stateful/modules/common/sensorissues/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateful/WinReconTools
# This actor looks for burst in usage
# of common recon tools used early
# during exploitation.
#######################################
Patrol( 'WinReconTools',
        initialInstances = 2,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/stateful/WinReconTools',
                      'analytics/stateful/modules/windows/recontools/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

#######################################
# stateful/MacReconTools
# This actor looks for burst in usage
# of common recon tools used early
# during exploitation.
#######################################
Patrol( 'MacReconTools',
        initialInstances = 2,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 500,
        actorArgs = ( 'analytics/stateful/MacReconTools',
                      'analytics/stateful/modules/osx/recontools/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

###############################################################################
# Hunts
###############################################################################
Patrol( 'SampleHunt',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 10000,
        actorArgs = ( 'analytics/hunt/SampleHunt',
                      'analytics/hunt/samplehunt/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )

Patrol( 'SuspectedDropperHunt',
        initialInstances = 1,
        maxInstances = None,
        relaunchOnFailure = True,
        onFailureCall = None,
        scalingFactor = 5000,
        actorArgs = ( 'analytics/hunt/SuspectedDropperHunt',
                      'analytics/hunt/suspecteddropperhunt/1.0' ),
        actorKwArgs = {
            'parameters' : {},
            'secretIdent' : 'hunt/8e0f55c0-6593-4747-9d02-a4937fa79517',
            'trustedIdents' : [ 'analysis/038528f5-5135-4ca8-b79f-d6b8ffc53bf5' ],
            'n_concurrent' : 5 } )