# ArcGIS Enterprise Linux 一键安装配置脚本

##概览
该自动化安装脚本支持ArcGIS Enterprise产品体系下：ArcGIS Sever 10.5、Portal  for ArcGIS 10.5、ArcGIS DataStore 10.5 Linux版本的一键安装。安装完成之后，会按照单机部署典型配置方案配置：Server联合Portal并且托管；DataStore配置关系以及缓存数据库。


 
##说明：
###文件结构
```
rpm/		ArcGIS所需依赖包
yum163/		Redhat 6/7所需的yum源
init.sh		自动安装配置脚本
config.sh	配置文件		
```

###**配置文件说明：（important）**

安装前需要按照自己的需要修改config.sh文件，该文件指定了一键安装所必须的许可文件、ArcGIS Enterprise安装文件ISO、以及账号密码等信息，如果没有正确的指定这些信息，自动化安装配置脚本是无法运行成功的。
```
newhostname="yourhostname"		
dnssuffix="yourdnssuffix"
arcgisuser='youraccout'
arcgisuserpwd='youraccoutpwd'
isofullpath='/path/to/arcgis.iso'
licensefullpath='/path/to/arcgis_ecp_license.ecp'
```
>newhostname

需要修改的安装目标机器的机器名

>dnssuffix            

需要修改的安装目标机器的DNS后缀

>arcgisuser

注意：该账号既是安装ArcGIS的操作系统账号，也是Server、Portal管理员的账号

>arcgisuserpwd

上述账号对应的密码

>isofullpath

ArcGIS Enterprise Linux 安装光盘（ISO文件）的完整路径、或者是插入了ArcGIS Enterprise Linux 安装光盘的CDROM路径

>licensefullpath

包含了Portal、Server正式版授权许可的许可文件完整路径

###运行方法
把该仓库下的所有脚本拷贝到目标Linux环境，如/root/oneclick 文件夹下，切换到该目录下，在shell中运行
```
bash init.sh
```
即可一键安装并且配置
###本机虚拟机快速安装说明：

 1. 把一键安装脚本所在文件夹共享出来，路径形如：\\本机ip\oneclickinstall
 2. 把ArcGIS Enterprise ISO所在文件夹共享出来，路径形如：\\本机ip\iso
 3. 在虚拟机环境中，加载本机的两个共享路径，代码如下：

```
(root 登录)
cd ~
mkdir share iso
mount -t cifs //本机ip/oneclickinstall -o username=你的windows账号,password=你的windows密码 ~/share
mount -t cifs //本机ip/iso -o username=你的windows账号,password=你的windows密码 ~/iso
cd share
bash init.sh
```
注，如果是RH6.5 或者7不支持mount cifs，可以把yum163文件夹下对应的脚本内容拷贝到虚拟机，运行可以自动安装cifs支持

##系统需求：

**ArcGIS支持版本**：目前仅支持ArcGIS Enterprise Linux 10.5 正式版（后续考虑添加老版以及Windows版本的支持）

**目前支持操作系统**：

 - Red Hat Enterprise Linux Server 6
 - Red Hat Enterprise Linux Server 7
 - SUSE Linux Enterprise Server 12
 - SUSE Linux Enterprise Server 11
 - Ubuntu Server LTS 16
 - CentOS Linux 6
 - CentOS Linux 7






