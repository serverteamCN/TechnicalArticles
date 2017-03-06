
# Linux上安装ArcGIS Enterprise超详细教程——以Redhat7.2上安装ArcGIS Enterprise 10.5为例
=================== 

    1 准备
    	1.1 防火墙的关闭（可选）
    	1.2 用户和组的创建
    	1.3 IP和机器名
    		1.3.1 编辑/etc/hostname
    		1.3.2 编辑/etc/hosts
    		1.3.3 主机名检测
    	1.4 准备安装包
    		1.4.1 拷贝安装包至/home/arcgis下
    		1.4.2 解压
    		1.4.3 修改权限
    2 安装和配置 ArcGIS for Server
    	2.1 安装前准备
    		2.1.1 编辑 limits.conf文件
    		2.1.2 诊断当前环境是否满足Server安装要求
    	2.2 安装 ArcGIS for Server
    	2.3 配置 ArcGIS for Server
    3 安装和配置 ArcGIS DataStore
    	3.1 安装前准备
    		3.1.1 设置 vm.swappiness
    		3.1.2 诊断当前环境是否满足 Data Store 安装要求
    	3.2 安装 ArcGIS DataStore
    	3.3 配置 ArcGIS Data Store
    4 安装和配置 Portal for ArcGIS
    	4.1 安装前准备
    		4.1.1 安装包文件
    		4.1.2 诊断当前环境是否满足 Portal for ArcGIS 安装要求
    	4.2 安装 Portal for ArcGIS
    	4.3 配置 Portal for ArcGIS
    5 安装和配置 Web Adaptor
    	5.1 安装前准备
    		5.1.1 安装 JDK
    			5.1.1.1 解压JDK
    			5.1.1.2 配置JDK环境变量
    		5.1.2 安装tomcat
    			5.1.2.1 解压tomcat
    			5.1.2.2 创建自签名证书
    			5.1.2.3 对tomcat启用ssl
    			5.1.2.4 启动和验证tomcat
    	5.2 安装和部署Web Adaptor
    		5.2.1 安装 Web Adaptor
    		5.2.2 部署Web Adaptor到tomcat下
    	5.3 配置 Web Adaptor
    		5.3.1 对Portal for ArcGIS配置名为arcgis的Web Adaptor
    		5.3.2 对ArcGIS for Server配置名为server的Web Adaptor
    6 将Server托管到Portal
    7 补充
    	7.1 对 ArcGIS for Server更新证书
    	7.2 对 Portal for ArcGIS更新证书
    	7.3 在客户端机器上安装证书



本文以Redhat7.2上安装ArcGIS Enterprise 10.5为例详细阐述了单机环境下ArcGIS Enterprise的完整安装。


## 1 准备
### 1.1 防火墙的关闭（可选）
停止防火墙

    [root@server127 home]# systemctl stop firwalld.service

禁用防火墙的开机启动

    [root@server127 home]# systemctl disable firewalld.service

查看防火墙状态

    [root@server127 home]# systemctl status firewalld.service

> **注意：**

> 单机环境下部署ArcGIS Enterprise时，可考虑仅开启 (1)80和443，确保外部客户端可通过web adaptor访问到Portal for ArcGIS或ArcGIS for Server服务页面；(2)当Web Adaptor层未启用ArcGIS for Server的管理功能时，则需开启6080和6443端口，确保外部客户端上的ArcMap向此环境下的ArcGIS for Server发布服务。关于ArcGIS Enterprise更多的端口信息，请参考下面的链接。

> 1. ArcGIS Server所用端口号： http://server.arcgis.com/en/server/latest/install/windows/ports-used-by-arcgis-server.htm
> 2. Portal for ArcGIS所用端口号：http://server.arcgis.com/en/portal/latest/administer/windows/ports-used-by-portal-for-arcgis.htm
> 3. ArcGIS Data Store所用端口号：http://server.arcgis.com/en/portal/latest/administer/windows/ports-used-by-arcgis-data-store.htm


### 1.2 用户和组的创建

    [root@server127 home]# groupadd esrichina
    [root@server127 home]# useradd -g esrichina -m arcgis
    [root@server127 home]# passwd arcgis

### 1.3 IP和机器名
ArcGIS Enterprise的安装要求计算机名是完全限定域名的形式。这一修改可通过编辑/etc/hostname和/etc/hosts两个文件实现。
#### 1.3.1 编辑/etc/hostname

    [root@server127 ~]# vi /etc/hostname

文件内容如下：

    agsenterprise

> **注意：**
> 主机名的设置也可通过运行hostnamectl set-hostname agsenterprise来实现。

#### 1.3.2 编辑/etc/hosts

    [root@server127 ~]# vi /etc/hosts
    
文件内容如下：

    127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
	::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
	192.168.220.127 agsenterprise.esrichina.com agsenterprise

> **注意：**
> 多网卡的环境下，建议删除localhost所在行。

#### 1.3.3 主机名检测
运行 hostname 和 hostname -f 进行主机名规范的检测。

    [root@agsenterprise home]# hostname
	agsenterprise
	[root@agsenterprise home]# hostname -f
	agsenterprise.esrichina.com

如上所示，主机名和完全限定域名显示无误，符合规范。


### 1.4 准备安装包
#### 1.4.1 拷贝安装包至/home/arcgis下
将 ArcGIS_Server_Linux_105_154052.tar.gz、ArcGIS_DataStore_Linux_105_154054.tar.gz、Web_Adaptor_Java_Linux_105_154055.tar.gz 和 Portal_for_ArcGIS_Linux_105_154053.tar.gz 拷贝到/home/arcgis目录下备用。
#### 1.4.2 解压
依次运行 tar -zxvf 对步骤**1.4.1**中四个安装包进行解压

    [root@agsenterprise arcgis]# tar -zxvf ArcGIS_Server_Linux_105_154052.tar.gz

#### 1.4.3 修改权限
依次运行 chown 和 chmod对步骤**1.4.2**解压后的四个文件夹修改权限。

    [root@agsenterprise arcgis]# chown -R arcgis:esrichina ArcGISServer/
	[root@agsenterprise arcgis]# chmod -R 755 ArcGISServer/
	
## 2 安装和配置 ArcGIS for Server
### 2.1 安装前准备
#### 2.1.1 编辑 limits.conf文件
编辑/etc/security/limits.conf文件，添加如下内容：

	    arcgis soft nofile 65535
        arcgis hard nofile 65535
        arcgis soft nproc 25059
        arcgis hard nproc 25059

#### 2.1.2 诊断当前环境是否满足Server安装要求
运行serverdiag脚本诊断当前环境是否满足ArcGIS for Server安装要求。

    [root@agsenterprise arcgis]# su - arcgis
    [arcgis@agsenterprise ~]$ ./ArcGISServer/serverdiag/serverdiag

当出现如下信息，说明当前环境满足需求，可安装ArcGIS for Server。     

    There were 0 failure(s) and 0 warning(s) found:

### 2.2 安装 ArcGIS for Server
这里利用console模式进行交互安装。

    [arcgis@agsenterprise ~]$ cd ArcGISServer/
	[arcgis@agsenterprise ArcGISServer]$ ./Setup -m console

安装完毕，显示如下信息，说明安装成功。

    
	Congratulations. ArcGIS Server 10.5 has been successfully installed to:
	/home/arcgis/arcgis/server
	You will be able to access ArcGIS Server Manager by navigating to
	http://agsenterprise.esrichina.com:6080/arcgis/manager.

	PRESS <ENTER> TO EXIT THE INSTALLER:

### 2.3 配置 ArcGIS for Server
在浏览器中输入步骤**2.2**中返回的ArcGIS Server Manager地址，自动跳转至ArcGIS for Server的6443端口，开始进行站点配置。

1 点击**创建新站点**。

![创建新站点](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2001.PNG)

2 设置主站点管理员账户的用户名和密码，点击**下一步**。

![设置主站点管理员账户的用户名和密码](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2002.PNG)

3 设置根服务器目录和配置存储的位置，点击**下一步**。

![设置站点的服务器目录和配置存储的位置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2003.PNG)

4 点击**完成**，直至安装成功。

![站点创建成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2004.PNG)

## 3 安装和配置 ArcGIS DataStore
### 3.1 安装前准备
#### 3.1.1 设置 vm.swappiness 和 vm.max_map_count
设置vm.swappiness和vm.max_map_count的值，以满足时空大数据分析的需要。

    [root@agsenterprise arcgis]# echo 'vm.max_map_count = 262144' >> /etc/sysctl.conf
    [root@agsenterprise arcgis]# echo 'vm.swappiness = 1' >> /etc/sysctl.conf

运行如下命令使上述变更生效。

    [root@agsenterprise arcgis]# /sbin/sysctl -p

#### 3.1.2 诊断当前环境是否满足 Data Store 安装要求
运行datastorediag脚本诊断当前环境是否满足ArcGIS DataStore的安装要求。

    [root@agsenterprise arcgis]# su - arcgis
    [arcgis@agsenterprise ~]$ ArcGISDataStore_Linux/datastorediag/datastorediag

当出现如下信息，说明当前环境满足需求，可安装ArcGIS DataStore。     

    There were 0 failure(s) and 0 warning(s) found:

### 3.2 安装 ArcGIS DataStore
这里利用silent模式进行静默安装。

    [arcgis@agsenterprise ~]$ cd ArcGISDataStore_Linux/
    [arcgis@agsenterprise ArcGISDataStore_Linux]$ ./Setup -m silent -l Yes
 
 安装完毕，显示如下信息，说明安装成功。
 
    ...ArcGIS Data Store 10.5 installation is complete.
	You will be able to configure ArcGIS Data Store 10.5 by navigating to https://localhost:2443/arcgis/datastore.

### 3.3 配置 ArcGIS Data Store
在浏览器中输入ArcGIS Data Store的访问地址 https://agsenterprise.esrichina.com:2443/arcgis/datastore/ ,开始进行 ArcGIS Data Store的配置。

1 输入步骤**2**中的 ArcGIS Server 的地址以及步骤**2.3**中设置的ArcGIS for Server主站点管理员账户的用户名和密码 ，点击**下一步**。

![指定ArcGIS Data Store所配置的GIS Server的URL和主站点管理员用户名密码](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2005.PNG)

2 设置内容目录的位置，点击**下一步**。

![设置ArcGIS Data Store的内容目录的位置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2006.PNG)

3 根据需要，选择配置关系型、切片缓存型和时空型的Data Store，点击**下一步**。

![选择要配置的Data Store的类型](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2007.PNG)

4 点击**完成**，直至安装成功。

![ArcGIS Data Store配置成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2008.PNG)

## 4 安装和配置 Portal for ArcGIS
### 4.1 安装前准备
#### 4.1.1  安装包文件
安装dos2unix。

    [root@agsenterprise arcgis]# yum install dos2unix

#### 4.1.2 诊断当前环境是否满足 Portal for ArcGIS 安装要求
运行portaldiag脚本诊断当前环境是否满足 Portal for ArcGIS 的安装要求。

    [arcgis@agsenterprise ~]$ PortalForArcGIS/portaldiag/portaldiag

当出现如下信息，说明当前环境满足需求，可安装Portal for ArcGIS。     

    There were 0 failure(s) and 0 warning(s) found:

### 4.2 安装 Portal for ArcGIS
这里利用console模式进行交互安装。。

    [arcgis@agsenterprise ~]$ cd PortalForArcGIS/
    [arcgis@agsenterprise PortalForArcGIS]$ ./Setup -m console
 
 安装完毕，显示如下信息，说明安装成功。

    Congratulations. Portal for ArcGIS 10.5 has been successfully installed to:
	/home/arcgis/arcgis/portal
	
	You will be able to access Portal for ArcGIS 10.5 by navigating to
	https://localhost:7443/arcgis/home.

### 4.3 配置 Portal for ArcGIS
在浏览器中输入Portal for ArcGIS的访问地址 https://agsenterprise.esrichina.com:7443/arcgis/home/ ，开始进行Portal for ArcGIS的配置。

1 点击**CREATE NEW PORTAL**

![创建新门户站点](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2009.PNG)

2 设置初始管理员账户信息和Portal for ArcGIS站点的内容目录，点击**CREATE**开始创建。

![配置 Portal for ArcGIS的管理员账户和内容目录等信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2010.PNG)

3 在弹出的**Account Created**界面上点击 OK，完成Portal for ArcGIS的配置 。

![Portal for ArcGIS初始管理员账户创建成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2011.PNG)

页面自动导航至新的页面，要求配置Web Adaptor。

## 5 安装和配置 Web Adaptor

### 5.1 安装前准备
#### 5.1.1 安装 JDK
##### 5.1.1.1 解压JDK

    [root@agsenterprise home]# tar -zxvf jdk-8u111-linux-x64.tar.gz
    [root@agsenterprise home]# mv jdk1.8.0_111/ jdk8

##### 5.1.1.2 配置JDK环境变量
1 编辑/etc/profile，配置JDK环境变量。

    # /etc/profile
    JAVA_HOME=/home/jdk8
    CLASSPATH=.:$JAVA_HOME/lib/tools.jar:$JAVA_HOME/lib/tools.jar
    PATH=$JAVA_HOME/bin:$PATH
    export JAVA_HOME CLASSPATH PATH

2 运行 source /etc/profile，使JDK环境变量配置生效。

3 验证JDK配置

    [root@agsenterprise home]# java -version
	java version "1.8.0_111"
	Java(TM) SE Runtime Environment (build 1.8.0_111-b14)
	Java HotSpot(TM) 64-Bit Server VM (build 25.111-b14, mixed mode)

出现上述信息，Java版本是1.8.0_111，说明JDK环境变量配置成功。

#### 5.1.2 安装tomcat
##### 5.1.2.1 解压tomcat

    [root@agsenterprise home]# tar -zxvf apache-tomcat-8.0.32.tar.gz
    [root@agsenterprise home]# mv apache-tomcat-8.0.32 tomcat8

##### 5.1.2.2 创建自签名证书
1 创建私钥和证书请求

    [root@agsenterprise home]# openssl req -newkey rsa:2048 -nodes -keyout /home/tomcat8/ssl/agsenterprise.key -x509 -days 365 -out /home/tomcat8/ssl/agsenterprise.crt

输入自签名证书创建所需的参数。创建自签名证书时，Common Name输入的是当前机器的完全限定域名即agsenterprise.esrichina.com。

    Country Name (2 letter code) [XX]:CN
	State or Province Name (full name) []:Beijing
	Locality Name (eg, city) [Default City]:Beijing
	Organization Name (eg, company) [Default Company Ltd]:EsriChina
	Organizational Unit Name (eg, section) []:TechSupport
	Common Name (eg, your name or your server's hostname) []:agsenterprise.esrichina.com
	Email Address []:zhangs@esrichina.com.cn

2 创建自签名证书

    [root@agsenterprise home]# openssl pkcs12 -inkey /home/tomcat8/ssl/agsenterprise.key -in /home/tomcat8/ssl/agsenterprise.crt -export -out /home/tomcat8/ssl/agsenterprise.pfx


##### 5.1.2.3 对tomcat启用ssl
编辑tomcat的server.xml文件，1) 将8080端口号修改为80；2) 将8443端口修改为443；3) 取消端口号8443对应的connector的注释，并启用ssl。

    [root@agsenterprise home]# vi tomcat8/conf/server.xml

1 将8080端口号修改为80。

    <Connector port="80" protocol="HTTP/1.1"
               connectionTimeout="20000"
               redirectPort="443" />
2 取消端口号8443对应的connector的注释，将8443端口修改为443，并启用ssl。

    <Connector port="443" protocol="org.apache.coyote.http11.Http11NioProtocol"
               maxThreads="150" SSLEnabled="true" scheme="https" secure="true"
               clientAuth="false" sslProtocol="TLS" keystoreFile="/home/tomcat8/ssl/agsenterprise.pfx" keystoreType="pkcs12" keystorePass="Super123" />

##### 5.1.2.4 启动和验证tomcat
运行startup.sh启动tomcat。

    [root@agsenterprise home]# cd tomcat8/bin/
    [root@agsenterprise bin]# ./startup.sh
	Using CATALINA_BASE:   /home/tomcat8
	Using CATALINA_HOME:   /home/tomcat8
	Using CATALINA_TMPDIR: /home/tomcat8/temp
	Using JRE_HOME:        /home/jdk8/jre
	Using CLASSPATH:       /home/tomcat8/bin/bootstrap.jar:/home/tomcat8/bin/tomcat-juli.jar
	Tomcat started.

验证tomcat启动是否成功。

![Web Server - tomcat 配置成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2012.PNG)

### 5.2 安装和部署Web Adaptor
#### 5.2.1 安装 Web Adaptor
以静默模式安装Web Adaptor。

    [arcgis@agsenterprise ~]$ WebAdaptor/Setup -m silent -l Yes

看到如下信息，说明Web Adaptor安装成功。

    ...ArcGIS Web Adaptor (Java Platform) 10.5 installation is complete.

#### 5.2.2 部署Web Adaptor到tomcat下
依次部署名为arcgis和server的Web Adaptor应用到 tomcat下，用于实现对Portal for ArcGIS和ArcGIS for Server的配置。

    [root@agsenterprise home]# cp /home/arcgis/webadaptor10.5/java/arcgis.war /home/tomcat8/webapps/arcgis.war
    [root@agsenterprise home]# cp /home/arcgis/webadaptor10.5/java/arcgis.war /home/tomcat8/webapps/server.war

### 5.3 配置 Web Adaptor
当通过浏览器对Portal for ArcGIS和ArcGIS for Server配置Web Adaptor时，要求必须在Web Adaptor所在的机器上。因此，当从非Web Adaptor所在机器的其他客户端配置Web Adaptor时，需要以命令行的形式。
#### 5.3.1 对Portal for ArcGIS配置名为arcgis的Web Adaptor

    [arcgis@agsenterprise ~]$ cd webadaptor10.5/java/tools/
    [arcgis@agsenterprise tools]$ ./configurewebadaptor.sh -m portal -w https://agsenterprise.esrichina.com/arcgis/webadaptor -g https://agsenterprise.esrichina.com:7443 -u portaladmin -p Super123

返回** Successfully Registered.**说明配置成功，即可通过webadaptor访问Portal for ArcGIS。

![对 Portal for ArcGIS 配置 Web Adaptor 成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2013.PNG)

#### 5.3.2 对ArcGIS for Server配置名为server的Web Adaptor

    [arcgis@agsenterprise tools]$ ./configurewebadaptor.sh -m server -w https://agsenterprise.esrichina.com/server/webadaptor -g https://agsenterprise.esrichina.com:6443 -u siteadmin -p Super123 -a false

返回** Successfully Registered.**说明配置成功，即可通过webadaptor访问ArcGIS for Server。

![对 ArcGIS for Server 配置 Web Adaptor 成功](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2015.PNG)

## 6 将Server托管到Portal
1 登录 Portal for ArcGIS。
 
![登录Portal for ArcGIS](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2014.PNG)

2 依次点击**My Organization**->**EDIT SETTINGS**->**Servers**，然后点击 **ADD SERVER**。

3 在弹出的**Add ArcGIS Server**对话框上设置Services URL、Administration URL，和主站点管理员账户的用户名和密码，点击**ADD**。

![添加 ArcGIS Server](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2016.PNG)

4 对**Hosting Server**选中联合的Server，即agsenterprise.esrichina.com/server。

![选择托管服务器](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2017.PNG)

5 点击**SAVE**保存。

## 7 补充
在单机环境下，为了确保ArcGIS for Server、Portal for ArcGIS和Web 服务器三个层面证书的统一，可将ArcGIS for Server和Portal for ArcGIS的证书更新为Web服务器的同一证书。
### 7.1 对 ArcGIS for Server更新证书
1 访问 ArcGIS for Server 的 admin 页面，即 https://agsenterprise.esrichina.com:6443/arcgis/admin/，输入用户名和密码登录。

2 导航至 **machines** -> Machines下机器名，如**AGSENTERPRISE.ESRICHINA.COM** -> **sslcertificates**，点击**importExistingServerCertificate**。输入agsenterprise.pfx的路径和密码，设置证书别名，点击 **Submit**。

![向ArcGIS for Server导入自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2020.PNG)

3 返回至Machines - 机器名即**Machine - AGSENTERPRISE.ESRICHINA.COM**页面，点击**edit**。

![编辑现有证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2021.PNG)

4 在**Edit Machine**页面上，，设置 **Web server SSL Certificate**的值为步骤**2**中的证书别名如 **agsenterprise**以引用上述证书，点击 **Save Edits**。

![更新ArcGIS for Server的证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2022.PNG)

如上，完成了对 ArcGIS for Server 的证书更新。

### 7.2 对 Portal  for ArcGIS更新证书
1 访问 Portal for ArcGIS 的admin页面，即 https://agsenterprise.esrichina.com/arcgis/portaladmin/ ，输入用户名和密码登录。

2 导航至 **security** -> **sslCertificates**，点击**importExistingServerCertificate**。输入agsenterprise.pfx的路径和密码，设置证书别名，点击 **import**。

![导入自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2018.PNG)

3 在 **sslCertificate** 页面上点击 **Update**。

4 在 **Update Web Server Certificate** 页面上，输入步骤**2**中的证书别名引用上述证书，点击  **Update**。

![更新Portal for ArcGIS的自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2019.PNG)

如上，完成了对Portal for ArcGIS的证书更新。

### 7.3 在客户端机器上安装证书
将证书安装到计算机的受信任的根证书颁发机构。

1 在浏览器中打开 Portal for ArcGIS，如https://agsenterprise.esrichina.com/arcgis/home/。

2 点击 **Internet 选项** -> **安全**，选中 **受信任的站点**，点击 **站点**，将 https://agsenterprise.esrichina.com  **添加** 到 **受信任的站点** 列表。

![将站点加入受信任站点](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Linux%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2023.PNG)

3 点击**证书错误**，在弹出的**不受信任的证书**对话框中，点击**查看证书**。

4 在弹出的**证书**对话框中，点击**安装证书**。

5 选择弹出位置**本地计算机**，点击**下一步**。

6 指定**将所有的证书都放入下列存储**并选中**受信任的根证书办法机构**，点击**确定**。

7 点击**下一步**->**完成**，直至证书安装成功。

![在客户端上安装自签名证书至受信任的根证书颁发机构](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%AE%89%E8%A3%85%E8%AF%81%E4%B9%A6.gif)
