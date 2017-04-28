# Linux上ArcGIS 10.5 GeoAnalytics集群环境部署指南 #

Linux操作系统版本：Red Hat Enterprise Linux 6.8 Desktop

## 1. 集群环境架构 ##
集群中共12个节点，其中1个Portal节点，1个Server节点作为托管服务器，5个GeoAnalytics(下文中简称GA)节点作为矢量大数据分析服务器，1个关系型（Relational）DataStore节点，4个时空大数据（Spatiotemporal) DataStore节点。其中Portal节点和GA集群需要安装ArcGIS Webadaptor，由于托管服务器只有一个Server节点，可以选择不必安装WebAdaptor。如下所示：
    
    机器编号 功能                         所需软件
    
    gis034  Portal                       Tomcat、Portal、WebAdaptor
    
    gis035  Hosting Server               Server
     
    gis041  DataStore:Relational         DataStore
    
    gis042  DataStore:Spatiotemporal     DataStore
    
    gis043  DataStore:Spatiotemporal     DataStore
    
    gis044  DataStore:Spatiotemporal     DataStore
    
    gis045  DataStore:Spatiotemporal     DataStore
    
    gis061  GA Server                    Tomcat、Server、WebAdaptor
    
    gis062  GA Server                    Server
    
    gis063  GA Server                    Server
    
    gis064  GA Server                    Server
    
    gis065  GA Server                    Server


## 2. 安装前环境检查 ##

2.1.通过date命令检查12个节点上时间是否同步：

    [root@gis034 ~]# date
    Thu Apr 27 13:13:40 CST 2017

2.2.创建用户组和arcgis用户：

    [root@gis034 ~]# groupadd arcgis
    [root@gis034 ~]# useradd -g arcgis -m arcgis
    [root@gis034 ~]# passwd arcgis

并通过id命令检查各节点上用户是否一致：

	[arcgis@gis034 root]$ id arcgis
	uid=500(arcgis) gid=500(arcgis) groups=500(arcgis)

2.3.修改各节点机器名：

    [arcgis@gis034 root]$ vim /etc/sysconfig/network
按`i`进入编辑模式，修改HOSTNAME：

    HOSTNAME=gis034.arcgisonline.cn

依次按`ESC,:,wq！`保存编辑并退出

2.4.重启机器使机器名修改生效：

    [root@gis034 ~]# reboot

2.5.重启后检查机器名是否已成功修改：

    [root@gis034 ~]# hostname
    gis034.arcgisonline.cn

2.6.（可选）在各节点上建立/gis目录，将软件安装包所在的共享存储目录挂载至本地的/gis目录下：

    [root@gis034 ~]# chmod –R 777 /gis
    [root@gis034 ~]# mount -t nfs 10.10.20.20:/softwares /gis

编辑/etc/fstab，添加一行：

     10.10.20.20:/softwares /gis nfs defaults 0 0

以保证机器重启后可自动挂载该目录

2.7.关闭各节点防火墙：

    [root@gis034 ~]# service iptables stop
    iptables: Setting chains to policy ACCEPT: filter  [  OK  ]
    iptables: Flushing firewall rules: [  OK  ]
    iptables: Unloading modules:   [  OK  ]

关闭防火墙开机自动启动：

    [root@gis034 ~]# chkconfig iptables off

关闭SELINUX，编辑/etc/selinux/config, 并设置SELINUX为disabled：

    [root@gis034 ~]# vim /etc/selinux/config
    
    
    # This file controls the state of SELinux on the system.
    # SELINUX= can take one of these three values:
    # enforcing - SELinux security policy is enforced.
    # permissive - SELinux prints warnings instead of enforcing.
    # disabled - No SELinux policy is loaded.
    SELINUX=disabled
    # SELINUXTYPE= can take one of these two values:
    # targeted - Targeted processes are protected,
    # mls - Multi Level Security protection.
    SELINUXTYPE=targeted

2.8.如果没有DNS服务器，则需要在各节点上修改hosts文件，将所有节点的ip和机器名加入hosts：
    
    [arcgis@gis034 tools]$ vim /etc/hosts
    
    127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
    ::1 localhost localhost.localdomain localhost6 localhost6.localdomain6
    
    10.10.20.34  gis034.arcgisonline.cn  gis034.arcgisonline.cn
    10.10.20.35  gis035.arcgisonline.cn  gis035.arcgisonline.cn
    10.10.20.40  gis040.arcgisonline.cn  gis040.arcgisonline.cn
    10.10.20.41  gis041.arcgisonline.cn  gis041.arcgisonline.cn
    10.10.20.42  gis042.arcgisonline.cn  gis042.arcgisonline.cn
    10.10.20.43  gis043.arcgisonline.cn  gis043.arcgisonline.cn
    10.10.20.44  gis044.arcgisonline.cn  gis044.arcgisonline.cn
    10.10.20.45  gis045.arcgisonline.cn  gis045.arcgisonline.cn
    10.10.20.61  gis061.arcgisonline.cn  gis061.arcgisonline.cn
    10.10.20.62  gis062.arcgisonline.cn  gis062.arcgisonline.cn
    10.10.20.63  gis063.arcgisonline.cn  gis063.arcgisonline.cn
    10.10.20.64  gis064.arcgisonline.cn  gis064.arcgisonline.cn
    10.10.20.65  gis065.arcgisonline.cn  gis065.arcgisonline.cn

保存修改后在各节点中测试是否能ping通其他节点：

    [arcgis@gis034 tools]$ ping gis061.arcgisonline.cn
    PING gis061.arcgisonline.cn (10.10.20.61) 56(84) bytes of data.
    64 bytes from gis061.arcgisonline.cn (10.10.20.61): icmp_seq=1 ttl=64 time=0.015 ms
    64 bytes from gis061.arcgisonline.cn (10.10.20.61): icmp_seq=2 ttl=64 time=0.014 ms

2.9.编辑各节点的/etc/security/limits.conf文件，添加如下内容：

    arcgis soft nofile 65535
    arcgis hard nofile 65535
    arcgis soft nproc 25059
    arcgis hard nproc 25059

保存修改后切换至arcgis账户查看是否已成功修改：

    [root@gis034 ~]# su arcgis
    [arcgis@gis034 root]$ ulimit -Sn
    65535
    [arcgis@gis034 root]$ ulimit -Su
    25059
    [arcgis@gis034 root]$ ulimit -Hn
    65535
    [arcgis@gis034 root]$ ulimit -Hu
    25059

2.10.在Portal节点上安装dos2unix依赖包：

    [root@gis034 ~]# rpm -Uvh /gis/lzrhelcomplete/softwares/dos2unix-3.1-37.el6.x86_64.rpm 

2.11.在Spatiotemporal DataStore各节点上修改vm.swappiness 和 vm.max_map_count值：

    [root@gis045 ~]# echo 'vm.max_map_count = 262144' >> /etc/sysctl.conf
    [root@gis045 ~]# echo 'vm.swappiness = 1' >> /etc/sysctl.conf

使修改生效：

    [root@gis045 ~]# /sbin/sysctl -p


## 3. 安装软件 ##
将所有ArcGIS软件的安装包（ArcGIS_Server_Linux_105_154052.tar.gz、ArcGIS_DataStore_Linux_105_154054.tar.gz、Web_Adaptor_Java_Linux_105_154055.tar.gz、Portal_for_ArcGIS_Linux_105_154053.tar.gz）分别解压至/gis目录下：

    [root@gis035 gis]# tar -zxvf ArcGIS_Server_Linux_105_154052.tar.gz

依次修改解压后的四个文件夹的权限：

    [root@gis035 gis]# chown -R arcgis:arcgis ArcGISServer/
	[root@gis035 gis]# chmod -R 755 ArcGISServer/


3.1.安装ArcGIS for Server（gis035，gis061-gis065）

切换至arcgis账户，运行serverdiag脚本诊断当前环境是否满足ArcGIS for Server安装要求：

    [root@gis035 gis]# su - arcgis
    [arcgis@gis035 ~]$ ./ArcGISServer/serverdiag/serverdiag

当出现如下信息，说明当前环境满足需求，可安装ArcGIS for Server：     

    There were 0 failure(s) and 0 warning(s) found:

通过console模式根据提示完成安装：

    [arcgis@gis035 ~]$ cd ArcGISServer/
	[arcgis@gis035 ArcGISServer]$ ./Setup -m console

安装完毕，显示如下信息，说明安装成功：
    
	Congratulations. ArcGIS Server 10.5 has been successfully installed to:
	/home/arcgis/arcgis/server
	You will be able to access ArcGIS Server Manager by navigating to
	http://gis035.arcgisonline.cn:6080/arcgis/manager.

	PRESS <ENTER> TO EXIT THE INSTALLER:

3.2.安装Portal for ArcGIS

运行portaldiag脚本诊断当前环境是否满足 Portal for ArcGIS 的安装要求：

    [arcgis@gis034 ~]$ PortalForArcGIS/portaldiag/portaldiag

当出现如下信息，说明当前环境满足需求，可安装Portal for ArcGIS

    There were 0 failure(s) and 0 warning(s) found:

通过console模式根据提示完成安装：

    [arcgis@gis034 ~]$ cd PortalForArcGIS/
    [arcgis@gis034 PortalForArcGIS]$ ./Setup -m console
 
 安装完毕，显示如下信息，说明安装成功：

    Congratulations. Portal for ArcGIS 10.5 has been successfully installed to:
	/home/arcgis/arcgis/portal
	
	You will be able to access Portal for ArcGIS 10.5 by navigating to
	https://localhost:7443/arcgis/home.

3.3.安装DataStore（gis041-gis045）

运行datastorediag脚本诊断当前环境是否满足ArcGIS DataStore的安装要求：

    [root@gis041 arcgis]# su - arcgis
    [arcgis@gis041 ~]$ ArcGISDataStore_Linux/datastorediag/datastorediag

当出现如下信息，说明当前环境满足需求，可安装ArcGIS DataStore：

    There were 0 failure(s) and 0 warning(s) found:

通过silent模式进行静默安装：

    [arcgis@gis041 ~]$ cd ArcGISDataStore_Linux/
    [arcgis@gis041 ArcGISDataStore_Linux]$ ./Setup -m silent -l Yes
 
 安装完毕，显示如下信息，说明安装成功：
 
    ...ArcGIS Data Store 10.5 installation is complete.
	You will be able to configure ArcGIS Data Store 10.5 by navigating to https://localhost:2443/arcgis/datastore.

3.4.安装WebAdaptor（gis034，gis061）

3.4.1 WebAdaptor依托于Tomcat，所以需要先安装Tomcat：

解压JDK：

    [root@gis034 softwares]# tar -zxvf jdk-8u111-linux-x64.tar.gz -C /usr/local

编辑/etc/profile，配置JDK环境变量：

    # /etc/profile
    export JAVA_HOME=/usr/local/jdk1.8.0_111
    export CLASS_PATH=.:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar
    export PATH=$JAVA_HOME/bin:$PATH


运行 source /etc/profile，使JDK环境变量配置生效.验证JDK配置：

    [root@gis034 home]# java -version
	java version "1.8.0_111"
	Java(TM) SE Runtime Environment (build 1.8.0_111-b14)
	Java HotSpot(TM) 64-Bit Server VM (build 25.111-b14, mixed mode)

出现上述信息，Java版本是1.8.0_111，说明JDK环境变量配置成功.

解压Tomcat：

    [root@gis034 softwares]# tar -zxvf apache-tomcat-8.0.32.tar.gz -C /usr/local

对tomcat开启https配置，因此需要生成tomcat自签名证书：

    [root@gis034 softwares]# cd /usr/local/
    [root@gis034 local]# keytool -genkey -alias tomcat -keyalg RSA -validity 36500 -keystore /usr/local/apache-tomcat-8.0.32/tomcat.keystore -keysize 2048

依次输入参数，第一项的first and last name输入的是当前机器的完全限定域名即 gis034.arcgisonline.cn,生成的证书在/usr/local/apache-tomcat-8.0.32，名称为tomcat.keystore.

编辑tomcat的server.xml文件:

    [root@gis034 home]# vim /usr/local/apache-tomcat-8.0.32/conf/server.xml

1) 将8080端口号修改为80:

    <Connector port="80" protocol="HTTP/1.1"
               connectionTimeout="20000"
               redirectPort="443" />

2) 取消端口号8443对应的connector的注释，将8443端口修改为443，并启用ssl:

    <Connector port="443" protocol="org.apache.coyote.http11.Http11NioProtocol"
               maxThreads="150" SSLEnabled="true" scheme="https" secure="true"
               clientAuth="false" sslProtocol="TLS"
               keystoreFile="/usr/local/apache-tomcat-8.0.32/tomcat.keystore"
               keystorePass="123456" />

运行startup.sh启动tomcat:

    [root@gis034 local]# cd apache-tomcat-8.0.32/bin/
    [root@gis034 bin]# ./startup.sh 
    Using CATALINA_BASE:   /usr/local/apache-tomcat-8.0.32
    Using CATALINA_HOME:   /usr/local/apache-tomcat-8.0.32
    Using CATALINA_TMPDIR: /usr/local/apache-tomcat-8.0.32/temp
    Using JRE_HOME:/usr/local/jdk1.8.0_111
    Using CLASSPATH:   /usr/local/apache-tomcat-8.0.32/bin/bootstrap.jar:/usr/local/apache-tomcat-8.0.32/bin/tomcat-juli.jar
    Tomcat started.

通过浏览器访问https://gis034.arcgisonline.cn,验证tomcat是否已成功启动：

![tomcat](http://i.imgur.com/tUtC3YP.jpg)

3.4.2 切换至WebAdaptor解压文件夹，以静默模式安装Web Adaptor:

    [arcgis@gis034 ~]$ WebAdaptor/Setup -m silent -l Yes

看到如下信息，说明Web Adaptor安装成功:

    ...ArcGIS Web Adaptor (Java Platform) 10.5 installation is complete.

部署名为arcgis的Web Adaptor应用到tomcat下：

    [root@gis034 home]# cp /home/arcgis/webadaptor10.5/java/arcgis.war /usr/local/apache-tomcat-8.0.32/webapps/arcgis.war

浏览器访问https://gis034.arcgisonline.cn/arcgis/webadaptor，出现以下页面即是部署成功：

![webadaptor](http://i.imgur.com/E6ZK3CD.jpg)

在GA集群的入口节点(gis061)上参照以上方式安装并部署WebAdaptor.


## 4. 配置集群 ##

4.1.配置Portal

访问https://gis034.arcgisonline.cn:7443/arcgis/home，创建Portal初始管理员账号。成功创建后页面自动导航至新的页面，要求配置Web Adaptor。

通过WebAdaptor安装目录下的工具将WebAdaptor与Portal关联：

    [root@gis034 ~]# su arcgis
    [arcgis@gis034 root]$ cd /home/arcgis/webadaptor10.5/java/tools/
    [arcgis@gis034 tools]$ ./configurewebadaptor.sh -m portal -w https://gis034.arcgisonline.cn/arcgis/webadaptor -g https://gis034.arcgisonline.cn:7443 -u arcgis -p arcgis123

返回** Successfully Registered.**说明配置成功,可通过WebAdaptor访问Portal：https://gis034.arcgisonline.cn/arcgis/home：

![portal](http://i.imgur.com/4tRhZXL.jpg)

在My Organization -- Edit Settings -- Security中将Portal设置为"Allow access to the portal through HTTPS only"模式：

![portalhttps](http://i.imgur.com/n5RJSiS.jpg)


4.2.配置托管服务器

创建托管服务器站点，通过浏览器访问https://gis035.arcgisonline.cn:6443/arcgis/manager, 选择 Create New Site，根据提示完成站点创建.

![newsite](http://i.imgur.com/ZDpZ1Aq.jpg)
![siteadmin](http://i.imgur.com/fCb00Io.jpg)
![config](http://i.imgur.com/2xNhC1a.jpg)
![loginsite](http://i.imgur.com/39lk0pn.jpg)

在站点的管理员页面中设置托管服务器为"HTTPS ONLY"模式，访问https://gis035.arcgisonline.cn:6443/arcgis/admin/security/config/update：

![hostinghttps](http://i.imgur.com/7rusO3C.jpg)

设置为HTTPS ONLY后服务器会重新启动，等待重启完成后，登录Portal -- My Organization -- Edit Settings -- Servers, 在Fedrated Servers下选择Add Server，添加刚配置完成的站点：

![addhosting](http://i.imgur.com/yuodXGf.jpg)

需要注意如果站点配置了WebAdaptor则第一项中Services URL填写通过WebAdaptor访问的服务地址.

访问Relational DataStore的地址（https://gis041.arcgisonline.cn:2443/arcgis/datastore/），将该DataStore注册至Server：

![dsrel](http://i.imgur.com/sitGCic.jpg)

选择DataStore的类型为Relational：

![rel](http://i.imgur.com/LKs0N87.jpg)

配置完成后，登录Server站点的管理员页面，验证下注册的DataStore状态是否正常，访问如https://gis035.arcgisonline.cn:6443/arcgis/admin/data/items/enterpriseDatabases/AGSDataStore_ds_tmiq9bpr/machines/GIS041.ARCGISONLINE.CN/validate的路径，检查Relational DataStore的状态：

![reldshealth](http://i.imgur.com/HUTPjbh.jpg)

访问Portal -- My Organization -- Edit Settings -- Servers，在该页面下方的Hosting Server中选择该站点为托管服务器：

![addhosting](http://i.imgur.com/m6g0VPf.jpg)

点击Save保存修改后，可以再次访问Portal -- My Organization -- Edit Settings -- Servers页面，选择Validate Servers，检查Portal与Server间的链接是否有效.


4.3.配置GA服务器

与创建托管服务器站点类似，创建GA服务器站点.通过浏览器访问https://gis061.arcgisonline.cn:6443/arcgis/manager, 选择 Create New Site，根据提示完成站点创建，并设置为HTTPS ONLY模式. 由于GA站点为集群，需要注册WebAdaptor作为单点出入口。通过gis061机器上的WebAdaptor工具注册站点至WebAdaptor：

    [root@gis061 ~]# su arcgis
    [arcgis@gis061 root]$ cd /home/arcgis/webadaptor10.5/java/tools/
    [arcgis@gis061 tools]$ ./configurewebadaptor.sh -m server -w https://gis061.arcgisonline.cn/arcgis/webadaptor -g https://gis061.arcgisonline.cn:6443 -u siteadmin -p siteadmin -a false

返回** Successfully Registered.**说明配置成功,可通过WebAdaptor访问GA站点服务目录：https://gis061.arcgisonline.cn/arcgis/rest.
登录Portal -- My Organization -- Edit Settings -- Servers, 在Fedrated Servers下选择Add Server，添加GA站点为Federated Server：

![ga](http://i.imgur.com/9XK66SL.jpg)

依次访问gis042-045的DataStore（https://gis045.arcgisonline.cn:2443/arcgis/datastore/），逐一为托管服务器配置Spatiotemporal类型的DataStore，如：

![dsspa](http://i.imgur.com/8mFbCbw.jpg)
![dsspa](http://i.imgur.com/Pzn8sY5.jpg)

配置完成后，登录Server站点的管理员页面，验证下注册的DataStore状态是否正常，访问如https://gis035.arcgisonline.cn:6443/arcgis/admin/data/items/nosqlDatabases/AGSDataStore_bigdata_bds_ir3mzk8x/machines/GIS045.ARCGISONLINE.CN/validate的路径，检查各Spatiotemporal DataStore的状态：

![spadshealth](http://i.imgur.com/4hSYYoM.jpg)

访问Portal -- My Organization -- Edit Settings -- Servers，在该页面下方的Feature Analysis - GeoAnalytics Tools中选择该站点为GA服务器：

![gaserver](http://i.imgur.com/dkUTdw1.jpg)

点击Save保存修改后，可以再次访问Portal -- My Organization -- Edit Settings -- Servers页面，选择Validate Servers，检查Portal与Server间的链接是否有效.

4.4.检查GA环境状态

配置了GA服务器后，应检查对应的各工具和系统服务是否已正常启动.

4.4.1.检查GeoAnalyticsManagement.GPServer是否启动，访问https://gis061.arcgisonline.cn:6443/arcgis/admin/services/System/GeoAnalyticsManagement.GPServer/status：

![gam](http://i.imgur.com/iLzK2RZ.jpg)

4.4.2.检查GeoAnalyticsTools.GPServer是否启动，访问https://gis061.arcgisonline.cn:6443/arcgis/admin/services/System/GeoAnalyticsTools.GPServer/status：

![gagp](http://i.imgur.com/04wiJKS.jpg)

4.4.3.检查Compute_Platform服务，访问https://gis061.arcgisonline.cn:6443/arcgis/admin/system/platformservices/39180567-fa26-4d56-9a58-40f9f6b5b512/status：

![spk](http://i.imgur.com/1tiXMzW.jpg)

4.4.4.检查Synchronization_Service服务，访问https://gis061.arcgisonline.cn:6443/arcgis/admin/system/platformservices/f612595c-0e9f-4656-8001-2c598fe80f5a/status：

![zk](http://i.imgur.com/WY3VkJj.jpg)

检查确认全部为启动状态后，可尝试在GA站点中注册Big Data File Share，访问GA站点Manager页面 -- Site -- Data Stores(https://gis061.arcgisonline.cn:6443/arcgis/manager/site.html)，选择注册Big Data File Share:

![bdfs](http://i.imgur.com/bDWU1WW.jpg)

在已注册的项目右侧点击编辑，查看是否成功生成了Manifest文件：

![manifest](http://i.imgur.com/2qGLOb9.jpg)

如果可以成功注册并识别Big Data File Share，可进行下一步，逐一添加其他的GA节点（gis062-065)至GA站点中，如果失败则先不要添加其他节点，先看日志排查出问题，已避免集群可能造成的影响.

全部节点添加完成后，修改GA平台可利用的最大内存和CPU资源比率，访问https://gis061.arcgisonline.cn:6443/arcgis/admin/system/properties/update，并添加限制值：

![max](http://i.imgur.com/nJBvZku.jpg)

该值的设置可参考官方帮助文档：http://server.arcgis.com/en/portal/latest/administer/windows/geoanalytics-settings.htm#GUID-0ED2B9A5-9F6B-4FEC-ABC5-DF5A749B3DD2

修改geoprocessing工具GeoAnalyticsTools的参数值，更改Maximum allowed compute cores per job (CPU)和Maximum allowed memory per job per machine (GB)为合适的数值，访问https://gis061.arcgisonline.cn:6443/arcgis/manager/service.html?name=GeoAnalyticsTools.GPServer&folder=System：

![gapara](http://i.imgur.com/bk6G7JJ.jpg)

该值的设置可参考官方帮助文档：http://server.arcgis.com/en/portal/latest/administer/windows/geoanalytics-settings.htm#ESRI_SECTION1_A4FF7CCD27BD43E4A5A63CA7B333B147

修改后再次检查上述的4项服务状态全部为正常后可开始执行分析工具.


## 5. 执行矢量大数据分析工具 ##

在Portal -- Map -- Analysis选项卡下选择GeoAnalytics Tools，选择对应的工具执行分析：

![tool](http://i.imgur.com/5smX4or.jpg)

