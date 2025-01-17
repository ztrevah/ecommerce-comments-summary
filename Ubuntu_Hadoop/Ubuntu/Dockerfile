# Use a lightweight base image
FROM ubuntu:24.04

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install required packages
RUN apt update && \
    apt install -y sudo \
                   iproute2 \
                   net-tools \
                   vim \
                   iputils-ping \
                   wget \
                   curl \
                   openjdk-8-jdk \
                   openssh-client \
                   openssh-server && \
    rm -rf /var/lib/apt/lists/*

RUN echo "root:123466"|chpasswd

# Thêm quyền sudo và tạo tài khoản người dùng mới
RUN useradd -m -s /bin/bash hadoopuser && \
    echo "hadoopuser:123466" | chpasswd && \
    usermod -aG sudo hadoopuser  

USER hadoopuser
WORKDIR /home/hadoopuser

# # Set JAVA_HOME environment variable
RUN JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac)))) && \
    echo "export JAVA_HOME=$JAVA_HOME" >> ~/.bashrc && \
    echo "export PATH=$JAVA_HOME/bin:$PATH" >> ~/.bashrc

ENV JAVA_HOME=${JAVA_HOME}\
    PATH=$JAVA_HOME/bin:$PATH

# Copy Hadoop files from the host machine into the container
ARG HADOOP_VERSION=3.3.6
COPY ./hadoop-$HADOOP_VERSION.tar.gz ./
# Extract Hadoop tar file
RUN tar -xvzf hadoop-$HADOOP_VERSION.tar.gz && \
    rm hadoop-$HADOOP_VERSION.tar.gz

# SCALA SETUP------------------------------------------------------
    RUN mkdir -p ~/.local/bin  
    RUN curl -fL https://github.com/coursier/coursier/releases/latest/download/cs-x86_64-pc-linux.gz | \
    gzip -d > ~/.local/bin/cs && chmod +x ~/.local/bin/cs

    # Thêm thư mục của người dùng vào PATH
    ENV PATH="/home/hadoopuser/.local/bin:${PATH}"

    # Chạy setup mà không yêu cầu tương tác
    RUN ~/.local/bin/cs setup --yes || true
    
    RUN cs install scala:2.12.15

    RUN echo "export PATH=$HOME/.local/share/coursier/bin:$PATH" >> /home/hadoopuser/.bashrc && \
    echo 'export LD_LIBRARY_PATH=$HADOOP_HOME/lib/native:$LD_LIBRARY_PATH' >> /home/hadoopuser/.bashrc

    ENV LD_LIBRARY_PATH=$HADOOP_HOME/lib/native:$LD_LIBRARY_PATH \
    PATH=$HOME/.local/share/coursier/bin:$PATH
# END SCALA -----------------------------------------------------------  


# SETUP SPARK---------------------------------------------------   
ARG SPARK_VERSION=3.4.4
COPY ./spark-3.4.4-bin-hadoop3.tgz ./
# Extract Hadoop tar file
RUN tar -xvf spark-3.4.4-bin-hadoop3.tgz && \
    rm spark-3.4.4-bin-hadoop3.tgz && \
    mv spark-3.4.4-bin-hadoop3 spark-3.4.4
 
RUN echo "export SPARK_HOME=/home/hadoopuser/spark-3.4.4" >> /home/hadoopuser/.bashrc && \
echo 'export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin' >> /home/hadoopuser/.bshrc

ENV SPARK_HOME=/home/hadoopuser/spark-3.4.4 \
    PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin 

    
# Thiết lập Spark master
RUN echo "spark.master yarn" >> ./spark-3.4.4/conf/spark-defaults.conf
# Sao chép tệp cấu hình và đổi tên bỏ .template
COPY spark_config/ ./spark-3.4.4/conf/

#Them thu vien elasticsearch vao jars cua spark
COPY ./elasticsearch-spark-30_2.12-8.7.0.jar ./spark-3.4.4/jars/
 
# END SETUP SPARK--------------------------------------------------- 

# # Set Hadoop environment variables
# Thêm các biến môi trường vào .bashrc
RUN echo 'export HADOOP_HOME=/home/hadoopuser/hadoop-3.3.6' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_INSTALL=$HADOOP_HOME' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_MAPRED_HOME=$HADOOP_HOME' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_COMMON_HOME=$HADOOP_HOME' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_HDFS_HOME=$HADOOP_HOME' >> /home/hadoopuser/.bashrc && \
    echo 'export YARN_HOME=$HADOOP_HOME' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop' >> /home/hadoopuser/.bashrc && \
    echo 'export PATH=$PATH:$HADOOP_HOME/sbin:$HADOOP_HOME/bin' >> /home/hadoopuser/.bashrc && \
    echo 'export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"' >> /home/hadoopuser/.bashrc

ENV HADOOP_HOME=/home/hadoopuser/hadoop-3.3.6 \
    HADOOP_INSTALL=$HADOOP_HOME \
    HADOOP_MAPRED_HOME=$HADOOP_HOME  \
    HADOOP_COMMON_HOME=$HADOOP_HOME  \
    HADOOP_HDFS_HOME=$HADOOP_HOME  \
    YARN_HOME=$HADOOP_HOME  \
    HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native \
    HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop \
    PATH=$PATH:$HADOOP_HOME/sbin:$HADOOP_HOME/bin \
    HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"

# Expose necessary ports
EXPOSE 8020 9864 8042 7077 4040 6066 19888 22 9870 8088 9000 8032

# Create Hadoop directories for namenode and datanode
RUN mkdir -p $HADOOP_HOME/data/namenode
RUN mkdir -p ./spark-3.4.4/code/elastic

COPY master/ ./hadoop-3.3.6/etc/hadoop/
COPY  code/elastic/ ./spark-3.4.4/code/elastic/

CMD ["/bin/bash"]
 