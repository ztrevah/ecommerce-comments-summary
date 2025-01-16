## Environment variables
- export HADOOP_HOME="/home/hadoopuser/hadoop"
- export HADOOP_COMMON_HOME=$HADOOP_HOME
- export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
- export HADOOP_HDFS_HOME=$HADOOP_HOME
- export HADOOP_MAPRED_HOME=$HADOOP_HOME
- export HADOOP_YARN_HOME=$HADOOP_HOME

## Hadoop config
### hadoop-env.sh
- Java version
### core-site.xml
- File system URI
- ...
### hdfs-site.xml
- Namenode, datanode directories
- No. replications
- ...
### workers
- Add worker nodes' hostname
