#基于Hadoop的ArcGIS大数据分析

**目录**
1 Hadoop的安装和集群配置
1.1 准备阶段
1.1.1 组和用户的创建
1.1.2 IP和机器名映射
			1.1.3 配置SSH免密码登录
		1.2 JDK的安装和配置（可选）
		1.3 Hadoop的安装和配置
		1.4 Hadoop的启动和验证
			1.4.1 Hadoop的启动
			1.4.2 Hadoop的验证
	2 Hadoop数据集准备
		2.1 创建件目录
		2.2 上传数据
		2.3 查看数据
	3 基于Hadoop数据的分析
	
-------------

##1 Hadoop的安装和集群配置

###1.1 准备阶段
该Hadoop集群基于Centos 7.2.1511操作系统，采用Hadoop 2.7.3和JDK1.7.0_75构建而成。集群中包含1个Master节点（机器名：master；IP：192.168.107.138）和1个Slave节点（机器名：slave；IP：192.168.107.139）。

####1.1.1 组和用户的创建    
在**master**节点上创建组esrichina和账户hadoop：

    [root@master ~]$ groupadd esrichina
    [root@master ~]$ useradd -g esrichina -m hadoop
    [root@master ~]$ passwd hadoop

在**slave**节点上执行相同操作，创建组esrichina和账户hadoop。

####1.1.2 IP和机器名映射
分别对**master**和**slave**两个节点编辑/etc/hosts文件，添加ip和机器名的映射关系。

    192.168.107.138 master.esrichina.com master
    192.168.107.139 slave.esrichina.com slave
    
####1.1.3 配置SSH免密码登录

 1. 修改/etc/ssh/sshd_config，取消如下两行的注释 。

	    RSAAuthentication yes
	    PubkeyAuthentication yes

 2. 输入命令ssh-keygen -t rsa生成key，不需输入密码直至结束。
 
		[root@master ~]$ su - hadoop
		[hadoop@master ~]$ ssh-keygen -t rsa

 3. 对**slave**节点执行步骤1和步骤2的操作。
 4. 把公钥文件复制到要访问的机器（**master**和**slave**）的hadoop用户目录下的.ssh目录中。

	    [hadoop@master ~]$ scp ~/.ssh/id_rsa.pub hadoop@master:/home/hadoop/.ssh/authorized_keys
	    [hadoop@master ~]$ scp ~/.ssh/id_rsa.pub hadoop@slave:/home/hadoop/.ssh/authorized_keys

 5. 测试由**master**节点免密码登录**slave**是否生效。

	     [hadoop@master ~]$ ssh hadoop@slave

###1.2 JDK的安装和配置（可选）

 1. 解压jdk
 
 2. 编辑/etc/profile，添加jdk环境变量。

	    # set the environments for jdk
	    JAVA_HOME=/home/jdk1.7.0_75
	    CLASSPATH=.:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar
	    PATH=$JAVA_HOME/bin:$PATH
	    export JAVA_HOME CLASSPATH PATH

 3. 运行 source 命令使配置的环境变量生效。

	    [root@master ~]$ source /etc/profile

 4. 运行 java -version 查看java配置是否生效。
 
 ![JDK配置生效](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/java%E7%8E%AF%E5%A2%83%E5%8F%98%E9%87%8F%E9%85%8D%E7%BD%AE%E7%94%9F%E6%95%88.png)
 
 
###1.3 Hadoop的安装和配置

 5. 下载和解压Hadoop，设置hadoop用户对文件夹hadoop-2.7.3的所有权。

 6. 修改hadoop用户的环境变量文件.bash_profile，将Hadoop可执行文件的位置添加到PATH变量中。

	    # Set the environments for hadoop
	    HADOOP_HOME=/home/hadoop/hadoop-2.7.3
	    PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
	    export HADOOP_HOME PATH

 7. 运行 source 命令使hadoop用户环境变量设置生效 。

	    [hadoop@master ~]$ source .bash_profile

 8. 创建Hadoop的tmp、data和name文件夹。

	    [hadoop@master ~]$ mkdir tmp hdfs hdfs/data hdfs/name

 9. Hadoop的配置，涉及【Hadoop安装位置】/etc/hadoop下的hadoop-env.sh、yarn-env.sh、slaves、core-site.xml、hdfs-site.xml、mapred-site.xml和yarn-site.xml共7个文件。
 
 1) 配置 hadoop-env.sh。如果$JAVA_HOME变量设置正确，也可不修改。

	    # The java implementation to use.
	    export JAVA_HOME=/home/jdk1.7.0_75
 2) 配置 yarn-env.sh。

	    # some Java parameters
	    # export JAVA_HOME=/home/y/libexec/jdk1.6.0/
	    export JAVA_HOME=/home/jdk1.7.0_75
 3) 配置slaves文件，用于存储所有slave节点的机器名。

	    slave
 4) 配置core-site.xml。	   

	    <!-- Put site-specific property overrides in this file. -->
	    <configuration>
	        <property>
		        <name>fs.defaultFS</name>
                <value>hdfs://master:9000</value>
	        </property>
	        <property>
                <name>hadoop.tmp.dir</name>
                <value>file:/home/hadoop/tmp</value>
	        </property>
		</configuration>

 5) 配置hdfs-site.xml。	

	    <!-- Put site-specific property overrides in this file. -->
	    <configuration>
		    <property>
			    <name>dfs.namenode.secondary.http-address</name>
		        <value>master:9001</value>
		    </property>
		    <property>
			    <name>dfs.namenode.name.dir</name>
		        <value>file:/home/hadoop/hdfs/name</value>
		    </property>
			<property>
				<name>dfs.datanode.data.dir</name>
		        <value>file:/home/hadoop/hdfs/data</value>
		    </property>
		    <property>
				<name>dfs.replication</name>
				<value>1</value>
			</property>
			<property>
				<name>dfs.webhdfs.enabled</name>
				<value>true</value>
			</property>
		</configuration>
 6) 由mapred-site.xml.template复制获得mapred-site.xml，并进行配置。

	    <!-- Put site-specific property overrides in this file. -->
	    <configuration>
		    <property>
			    <name>mapreduce.framework.name</name>
                <value>yarn</value>
	        </property>
	        <property>
                <name>mapreduce.jobhistory.address</name>
                <value>master:10020</value>
	        </property>
	        <property>
                <name>mapreduce.jobhistory.webapp.address</name>
                <value>master:19888</value>
	        </property>
	    </configuration>

 7) 配置yarn-site.xml。

	    <configuration>
	    <!-- Site specific YARN configuration properties -->
	        <property>
		        <name>yarn.nodemanager.aux-services</name>
                <value>mapreduce_shuffle</value>
	        </property>
	        <property>
				<name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name>
				<value>org.apache.hadoop.mapred.ShuffleHandler</value>
	        </property>
	        <property>
				<name>yarn.resourcemanager.address</name>
				<value>master:8032</value>
			</property>
			<property>
				<name>yarn.resourcemanager.scheduler.address</name>
				<value>master:8030</value>
			</property>
			<property>
				<name>yarn.resourcemanager.resource-tracker.address</name>
				<value>master:8031</value>
			</property>
			<property>
				<name>yarn.resourcemanager.admin.address</name>
				<value>master:8033</value>
			</property>
			<property>
				<name>yarn.resourcemanager.webapp.address</name>
				<value>master:8088</value>
			</property>
		</configuration> 


 10. 复制Hadoop到**slave**节点 

	    [hadoop@master ~]$ scp -r hadoop-2.7.3 hadoop@slave:/home/hadoop/
	    
###1.4 Hadoop的启动和验证

####1.4.1 Hadoop的启动

 11. 格式化 namenode 。

	    [hadoop@master ~]$ hdfs namenode -format

 如果看到successfully formatted和Exiting with status 0的提示，即说明格式化完毕。
 12. 启动NameNode和DataNode守护进程 。

	    [hadoop@master ~]$ start dfs.sh

 13. 启动ResourceManager和NodeManager守护进程 。

	    [hadoop@master ~]$ start yarn.sh
	    
####1.4.2 Hadoop的验证

 14. 运行 jps 查看**master**和**slave**节点上启动的进程 。

	    [hadoop@master ~]$ jps

 在**master**节点上存在4个进程，ResourceManager、NameNode、Jps和SecondaryNameNode；在**slave**节点上存在3个进程，NodeManager、DataNode和Jps。
 
 15. 查看集群状态 。

	    [hadoop@master ~]$ hdfs dfsadmin -report
	    
 ![Hadoop集群创建成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E9%9B%86%E7%BE%A4%E6%88%90%E5%8A%9F%E5%88%9B%E5%BB%BA%E9%AA%8C%E8%AF%81.png)
 
 Live datanodes (1) 说明集群成功建立。
 
##2 Hadoop数据集准备

###2.1 创建文件目录 

	    [hadoop@master data]$ hadoop fs -mkdir -p /usr/hadoop/greenDec24
 	      
###2.2 上传数据

	    [hadoop@master data]$ hadoop fs -put /home/greenDec24.csv /usr/hadoop/greenDec24

###2.3 查看数据

	    [hadoop@master data]$ hadoop fs -ls /usr/hadoop/greenDec24

##3 基于Hadoop数据的分析

 1. 登录 **ArcGIS for Server Manager**，点击 **Site**  ->  **Data Stores**。
 
 ![ArcGIS for Server Manager的Data Store页面](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%900.png)
 
 2. 在Data Stores设置页面上，点击 **Register** 旁边的 **Big Data File Share**，设置 **Type** 为 **HDFS**，输入 **Name** 和 **Path**，点击 **Create**。
 
 ![配置HDFS大数据文件共享](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%901.png)
 
 3. 点击 **编辑** 图标，在打开的 **Big Data File Share** 界面上选择待分析的数据集，点击 **保存**。
 
 ![选择数据集并保存](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%902.png)
 
 4. 登录Portal for ArcGIS，进入 **Map** 页，点击 **Analysis**  ->  **GeoAnalytics Tools**  ->  **Summarize Data**  ->  **Aggregate Points**，浏览至注册的数据集，点击 **ADD LAYER**。
 
 ![浏览至数据集](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%903.png)
 
 5. 输入所需参数，点击 **RUN ANALYSIS** 开始分析。
 
 ![输入分析所需参数](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%903.png)
 
 6. 得到分析结果。
 
 ![分析结果](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EHadoop%E7%9A%84ArcGIS%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%904.png)

 

