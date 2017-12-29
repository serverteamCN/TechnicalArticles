# Kerberos 简单配置攻略
## 一 Kerberos简史  
Kerberos是一种网络安全认证协议，最早由麻省理工研发，用来保护项目 Athena提供的网络服务器。这个协议以希腊神话中的人物Kerberos（或者Cerberus）命名，他在希腊神话中是Hades的一条凶猛的三头保卫神犬。  

![kerberos](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/Kerberos简单使用攻略01.png)

Internet是一个非常不安全的地方。在Internet中使用的很多协议并没有提供任何安全保障。一些站点尝试使用防火墙来解决网络安全问题。不幸的是，防火墙假设“坏蛋”都在外边，往往这是非常愚蠢的假设。现实情况是大多数计算机犯罪的毁灭事件都从内部发起。  

Kerberos作为网络安全问题的解决方案，使用强加密技术，以便客户端可以在不安全网络连接上向服务器端证明身份。在客户端和服务器端使用Kerberos证明彼此身份之后，它们也可以加密所有通信以确保隐私和数据的完整性。在系统设计上Kerberos采用C/S架构，基于DEC加密技术，支持客户端和服务器端双向认证。  

总之，Kerberos是一种网络安全问题的解决方案。它提供了认证和强加密工具用以在整个企业基于网络帮助你保护你的信息系统。  

在这篇文章写作时，Kerberos最新版本为2017年12月5日发布的krb5-1.16 版本。

## 二 Kerberos 基本原理

Kerberos是第三方的认证机制，通过它，用户和用户希望访问的服务依赖于Kerberos服务器彼此认证。这种机制也支持加密用户和服务之间的所有通信。Kerberos 服务器作为密钥分发中心，简称KDC。在高级别上，它包含三部分：  
- 用户和服务的数据库（即principals）以及他们各自的Kerberos 密码  
- 认证服务器（AS），执行初始认证并签发授权票据（TGT）  
- Ticket授予服务器（TGS）基于初始的TGT签发后续的服务票据（ST）  

关于AS, TGS , user client , Application server , TGT 以及ST的关系，可以参考下图：  

![架构原理](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/Kerberos简单使用攻略02.png)  


用户principal，从AS请求认证，AS返回一个使用用户principal的kerberos密码加密的TGT,它仅被用户principal和AS知晓。用户principal使用Kerberos密码本地解密这个TGT，并且从这个点开始，直到票据过期，用户principal可以使用这个TGT从TGS获取服务票据（ST）。

Kerberos 认证系统使用一系列的加密消息向验证机证明客户端正在以指定用户身份运行。Kerberos通过使用时间戳来减少需要基础校验的消息数量，除了“tikcket-granting”(TGS)服务被用来支持后续的认证外，不需要重复输入principal的密码。

最初，客户端和服务器端并没有共享加密密钥。无论何时客户端到一个新的验证机认证自己都依赖于AS生成的新的加密密钥，并且将其安全地分发给彼此。这个新的加密密钥叫做 session key， Kerberos ticket被用来分发它到验证机。

 
由于服务principal不可能每次提供密码来解密TGT，它会使用一个特定的文件，叫做keytab，这个文件包含了它的认证授权。
这种服务票据允许principal访问各种服务。Kerberos服务器控制的一套主机，用户和服务被称作一个域（realm）。

>注意：Kerberos是时间敏感型协议，在域内的所有主机必须是时间同步的。既使客户端的本地系统时间和KDC的差异小到5分钟，客户端都可能认证失败。  

## 三 Kerberos 安装部署

以下的测试过程是基于宿主在docker环境下的四台服务器hadoop01,hadoop02,hadoop03,hadoop04其中hadoop01作为服务器端KDC，其它三台机器作为客户端。

#### 1 系统环境
- 三台docker容器都基于统一的CentOS7
- 特殊说明：docker 环境下需要特别设置--priviledged=True 才能使用kerberos   
```
eg: docker run -it --name hadoop01 --hostname hadoop01.esrichina.com --privileged=true --mount source=hdfs_db,target=/home/hdfs_db hadoopbase 
```

#### 2 安装kerberos服务器端
##### 1）在hadoop01上部署服务器端软件
```	
$yum install krb5-libs krb5-server krb5-workstation 

```
##### 2）修改主配置文件/etc/krb5.conf，这个配置文件后续将被下发给所有kerberos客户端服务器。  

***确保默认realm设置为域名大写形式***    

```  
[root@hadoop01 etc]# cat /etc/krb5.conf
#Configuration snippets may be placed in this directory as well
includedir /etc/krb5.conf.d/

[logging]
 default = FILE:/var/log/krb5libs.log
 kdc = FILE:/var/log/krb5kdc.log
 admin_server = FILE:/var/log/kadmind.log

[libdefaults]
    default_realm = ESRICHINA.COM
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    forwardable = true
    udp_preference_limit = 1000000
    default_tkt_enctypes = des-cbc-md5 des-cbc-crc des3-cbc-sha1
    default_tgs_enctypes = des-cbc-md5 des-cbc-crc des3-cbc-sha1
    permitted_enctypes = des-cbc-md5 des-cbc-crc des3-cbc-sha1
[realms]
  ESRICHINA.COM = {
   kdc = hadoop01.esrichina.com:88
   admin_server = hadoop01.esrichina.com:749
   default_domain = esrichina.com
  }

[domain_realm]
  .esrichina.com = ESRICHINA.COM
  esrichina.com = ESRICHINA.COM  
  
```
##### 3）修改/var/kerberos/krb5kdc/kdc.conf配置
```

[root@hadoop01 etc]# cat /var/kerberos/krb5kdc/kdc.conf 
default_realm = ESRICHINA.COM

[kdcdefaults]
 kdc_ports = 0
 v4_mode = nopreauth

[realms]
 ESRICHINA.COM = {
	kdc_ports = 88
        admin_keytab = /etc/kadm5.keytab
        database_name = /var/kerberos/krb5kdc/principal
        acl_file = /var/kerberos/krb5kdc/kadm5.acl
        key_stash_file = /var/kerberos/krb5kdc/stash
        max_life = 10h 0m 0s
        max_renewable_life = 7d 0h 0m 0s
        master_key_type = des3-hmac-sha1
        supported_enctypes = arcfour-hmac:normal des3-hmac-sha1:normal des-cbc-crc:normal des:normal des:v4 des:norealm des:onlyrealm des:afs3
        default_principal_flags = +preauth
    }
```
##### 4）修改/var/kerberos/krb5kdc/kadm5.acl 配置
```
[root@hadoop01 etc]# cat /var/kerberos/krb5kdc/kadm5.acl  
*/admin@ESRICHINA.COM	*

```

这步配置的含义：所有匹配“ \*/admin@ESRICHINA.COM ”的principal都拥有全部权限 “*”

至此，服务器端环境基本搭建完成了，接下来开始创建KDC数据库用以保存kerberos 数据

##### 5）创建KDC数据库用以保存Kerberos 数据
```
[root@hadoop01 etc]# kdb5_util create -r  
 ESRICHINA.COM -s
```

创建完成后，可以检查下/var/kerberos/krb5kdc/目录，里面包含了相应的principal*文件：   
 
```
[root@hadoop01 etc]# ll /var/kerberos/krb5kdc/           
total 32  
-rw------- 1 root root   24 Dec 20 09:22 kadm5.acl
-rw------- 1 root root 1019 Dec 20 09:37 kadm5.keytab
-rw------- 1 root root  630 Dec 20 09:28 kdc.conf
-rw------- 1 root root 8192 Dec 21 02:27 principal
-rw------- 1 root root 8192 Dec 20 09:30 principal.kadm5
-rw------- 1 root root    0 Dec 20 09:30 principal.kadm5.lock
-rw------- 1 root root    0 Dec 21 02:27 principal.ok
-rw------- 1 root root   70 Dec 20 09:30 stash
```
##### 6）开始创建管理员和测试用户
```
[root@hadoop01 etc]# kadmin.local
kadmin.local:  addprinc root/admin
kadmin.local:  addprinc makl/admin
kadmin.local:  listprincs
kadmin.local:  exit
```

##### 7）启动Kerberos KDC 和kadmin daemons ：
正常情况，基于linux 7系统，可以通过以下命令启动服务：  

```
systemctl start krb5kdc.service    
systemctl start kadmin.service  
systemctl enable krb5kdc.service  
systemctl enable kadmin.service  

```

但是由于docker环境众所周知的bug ， systemctl start命令会遭遇“Failed to get D-Bus connection: Operation not permitted”错误，我通过以下方式开启kerberos守护进程:  

```
[root@hadoop01 sbin]# /usr/sbin/krb5kdc -start  
[root@hadoop01 sbin]# /usr/sbin/kadmind
```

OK，服务器端工作已经全部完成，接下来我们开始搭建kerberos客户端环境。

#### 3  安装kerberos 客户端
##### 1）在所有客户端机器中安装kerberos客户端软件：  

```
[root@hadoop02 etc]# yum -y install krb5-libs krb5-workstation  
[root@hadoop03 etc]# yum -y install krb5-libs krb5-workstation  
[root@hadoop04 etc]# yum -y install krb5-libs krb5-workstation  
```

##### 2）将之前在hadoop01 kerberos server上配置的/etc/krb5.conf文件拷贝到客户端机器  

```
[root@hadoop02 ssh]# scp root@hadoop01:/etc/krb5.conf /etc/krb5.conf  
krb5.conf                                     100%  828     1.8MB/s   00:00   

```
同理，拷贝到hadoop03和hadoop04服务器上  

```
[root@hadoop03 ssh]# scp root@hadoop01:/etc/krb5.conf /etc/krb5.conf  
[root@hadoop04 ssh]# scp root@hadoop01:/etc/krb5.conf /etc/krb5.conf  
  
```

这步操作需要你在集群内所有服务器上配置了ssh环境，允许使用scp命令。如果没有，可以通过nfs共享文件也可以。

#### 4 检测kerberos安全验证
kerberos支持在KDC上使用kadmin.local管理kerberos, 也支持使用kamin在远程客户端机器上管理kerberos。  

##### 1）在使用kadmin 之前，先通过kinit验证是否可以登陆：  

```
[root@hadoop03 ssh]# kinit makl/admin@ESRICHINA.COM
Password for makl/admin@ESRICHINA.COM:   
```

这步使用了principal + kerberos 密码的校验方式，如果校验正确，kerberos不会有任何提示，而是直接返回到命令行状态，接下来再输入kadmin命令，输入密码，即可进入kerberos管理状态。

##### 2）进入kadmin  
  
```
[root@hadoop03 ssh]# kadmin  
Authenticating as principal makl/admin@ESRICHINA.COM with password.   
Password for makl/admin@ESRICHINA.COM:   
```

##### 3）在kadmin环境中，通过list_principals命令列出当前kerberos server中所有的用户  

```
kadmin:  list_principals  
```


上述检测过程是通过客户端输入密码的方式来校验的，对于运行在客户端的程序上述方式显然不够便利，kerberos还提供了免交互式的验证方式，通过keytab来保存密钥，实现自动校验。


##### 4）创建key table(密钥表)命令  

###### 4.1）这些操作需要管理员权限执行，因此我们首先进入kamin：  
  
```
[root@hadoop01 krb5kdc]# kinit makl/admin@ESRICHINA.COM    
Password for makl/admin@ESRICHINA.COM:  
[root@hadoop01 krb5kdc]# kadmin  
Authenticating as principal makl/admin@ESRICHINA.COM with password.  
Password for makl/admin@ESRICHINA.COM:   
```

###### 4.2）在kadmin下，通过ktadd命令为用户principal创建密钥  
  
```
kadmin:  ktadd -k /var/kerberos/krb5kdc/kadm5.keytab makl/admin@ESRICHINA.COM
Entry for principal makl/admin@ESRICHINA.COM with kvno 3, encryption type arcfour-hmac added to keytab WRFILE:/var/kerberos/krb5kdc/kadm5.keytab.
Entry for principal makl/admin@ESRICHINA.COM with kvno 3, encryption type des3-cbc-sha1 added to keytab WRFILE:/var/kerberos/krb5kdc/kadm5.keytab.
Entry for principal makl/admin@ESRICHINA.COM with kvno 3, encryption type des-cbc-crc added to keytab WRFILE:/var/kerberos/krb5kdc/kadm5.keytab.  
```

###### 4.3）分发密钥表  

这个密钥表是服务器端和客户端免密认证的关键，也是服务器端和客户端最重要的秘密，因此创建好后，需要在集群内所有服务器上分发，用来后续的principal校验。  

这里我只举一个例子，将keytab通过scp命令从hadoop01服务器拷贝到hadoop03,牢记这个keytab需要在所有客户端和服务器端分发和保密：  

```
[root@hadoop03 krb5kdc]# scp root@hadoop01:/var/kerberos/krb5kdc/kadm5.keytab /var/kerberos/krb5kdc/kadm5.keytab
kadm5.keytab                                  100% 1220     2.1MB/s   00:00  
```
###### 4.4）验证免密登陆：  
  
```
[root@hadoop03 krb5kdc]# kinit -kt /var/kerberos/krb5kdc/kadm5.keytab makl/admin@ESRICHINA.COM
[root@hadoop03 krb5kdc]# kadmin -kt /var/kerberos/krb5kdc/kadm5.keytab -p makl/admin@ESRICHINA.COM
Authenticating as principal makl/admin@ESRICHINA.COM with keytab /var/kerberos/krb5kdc/kadm5.keytab.
kadmin:   
``` 

>提示：kadmin 命令中在输入principal之前，有一个-p 标识符，和kinit命令规则并不同，如果你忽略了，就可能遭遇登陆失败。

最后，简单总结几个常用的kerberos命令。

####5 常用kerberos 命令  

##### 1）退出kadmin  
  
```
kadmin:  exit  
```

##### 2）删除当前认证缓存 
 
```
[root@hadoop03 krb5kdc]# kdestroy  
```

##### 3）列出当前用户  
  
```  
[root@hadoop03 ssh]# klist
Ticket cache: FILE:/tmp/krb5cc_0
Default principal: makl/admin@ESRICHINA.COM

Valid starting     Expires            Service principal
12/21/17 02:27:47  12/21/17 12:27:47  krbtgt/ESRICHINA.COM@ESRICHINA.COM
	renew until 12/22/17 02:27:43
```

##### 4）删除已有principal  

```
[root@hadoop01 keytab]# kadmin.local
kadmin.local:  delprinc nn/esrichina.com@ESRICHINA.COM
Are you sure you want to delete the principal "nn/esrichina.com@ESRICHINA.COM"? (yes/no): yes
Principal "nn/esrichina.com@ESRICHINA.COM" deleted.
```

这篇文档只是我在配置kerberos过程中一些过程的总结，更详细的信息建议阅读kerberos的在线帮助。  

#### 6 靠谱的kerberos学习资源  

-麻省在线帮助：https://web.mit.edu/kerberos/krb5-latest/doc/  
-相关论文：https://web.mit.edu/kerberos/papers.html




