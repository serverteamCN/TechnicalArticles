通过SSH访问远程Linux服务器，可能是每一个熟悉Linux系统的工程师最熟悉不过的了，但是通过ssh免密登陆控制远程Linux服务器确是近些年来随着大数据的迅猛发展，在大型服务器集群下才浮现出来的普遍需求，我第一次接触SSH免密配置即是在配置hadoop集群的过程中。ssh免密配置对大型服务器集群的通信非常非常重要，这篇文章是用来梳理ssh免密相关的原理和关键配置过程。

## 理解SSH

**Secure Shell**（安全外壳协议，简称**SSH**）是一种加密的网络传输协议，可在不安全的网络中为网络服务提供安全的传输环境。SSH通过在网络中创建安全隧道来实现SSH客户端与服务器之间的连接。虽然任何网络服务都可以通过SSH实现安全传输，SSH最常见的用途还是远程登录系统，人们通常利用SSH来传输和远程执行命令。

SSH以**非对称加密**实现身份验证。最常用的身份验证有两种，一种方法是使用自动生成的公钥-私钥对来简单地加密网络连接，随后使用密码认证进行登录；第二种方法是人工生成一对公钥和私钥，通过生成的密钥进行认证，这样就可以在不输入密码的情况下登录。任何人都可以自行生成密钥，公钥需要放在待访问的机器上，而对应的私钥需要由用户自行保管，认证过程基于生成出来的私钥，但整个认证过程私钥本身并不会传输到网络中。今天的配置过程就是践行第二种认证方式。

## 准备测试环境

这次配置我们基于三台docker容器,主机名分别为hadoop01,hadoop02,hadoop03。

它们的系统环境是Centos 7

*在接下来的配置过程前确保集群内的所有服务器可以通过机器名或全域名通信，如果没有配置统一的DNS，可以通过配置所有服务器的hosts映射来简单替代。

例如：  

```  
[root@hadoop02 etc]# vim /etc/hosts
172.17.0.2      hadoop01.esrichina.com hadoop01
172.17.0.3      hadoop02.esrichina.com hadoop02
172.17.0.4      hadoop03.esrichina.com hadoop03
```
任务

在hadoop01服务器上通过ssh 免密访问hadoop02和hadoop03服务器。可以理解为hadoop01服务器作为ssh客户端，远程访问hadoop02和hadoop03，那hadoop02和hadoop03相当于ssh服务器端。

## 配置过程

### 1，安装openssh

\- 在所有机器上安装ssh客户端   
 
```  
[root@hadoop01 ~]#  yum -y install openssh-clients  
[root@hadoop02 ~]#  yum -y install openssh-clients  
[root@hadoop03 ~]#  yum -y install openssh-clients  
```

*客户端必须装，否则后面没办法使用scp命令传输文件。

-在hadoop02，hadoop03上安装ssh服务器端，并启动ssh服务  
  
```
[root@hadoop02 ~]# yum instsll openssh-server
[root@hadoop03 ~]# yum instsll openssh-server  
```

-修改sshd_config 允许root用户登陆  

```
[root@hadoop02 .ssh]# vim /etc/ssh/sshd_config
PermitRootLogin yes
[root@hadoop03 .ssh]# vim /etc/ssh/sshd_config
PermitRootLogin yes
```  

-启动ssd服务  

```
[root@hadoop02 ~]# systemctl restart sshd
[root@hadoop03 ~]# systemctl restart sshd  
```

### 2, 在客户端服务器hadoop01上创建公钥和私钥

```  
[root@hadoop01 /]# ssh-keygen -t rsa                                          *1
Generating public/private rsa key pair.
Enter file in which to save the key (/root/.ssh/id_rsa):  test_rsa    *2
Enter passphrase (empty for no passphrase):                              *3
Enter same passphrase again: 
Your identification has been saved in /root/.ssh/test_rsa.            *4
Your public key has been saved in /root/.ssh/test_rsa.pub.          *5
The key fingerprint is:
SHA256:6QdVD4E2S6x0O/PJ6NhciuQ03BaXm4o4luD1zIeJ6D0 [root@hadoop01.esrichina.com](mailto:root@hadoop01.esrichina.com)               *6
The key's randomart image is:
+---[RSA 2048]----+
|         . .+.   |
|        . B. o   |
|       . =.+ ..  |
|        .o* o    |
|       .S. O +   |
|    . ..=.+ B    |
|   . + @.%.+     |
|    o.E @.B      |
|   ....o .       |
+----[SHA256]-----+                                          
```
*1: ssh-keygen是用来生成密钥的工具， 参数-t rsa用来指明生成的密钥以rsa加密公钥算法加密。

**加餐**：RSA[公钥](https://baike.baidu.com/item/%E5%85%AC%E9%92%A5)[加密算法](https://baike.baidu.com/item/%E5%8A%A0%E5%AF%86%E7%AE%97%E6%B3%95)是1977年由[罗纳德·李维斯特](https://baike.baidu.com/item/%E7%BD%97%E7%BA%B3%E5%BE%B7%C2%B7%E6%9D%8E%E7%BB%B4%E6%96%AF%E7%89%B9)（Ron Rivest）、[阿迪·萨莫尔](https://baike.baidu.com/item/%E9%98%BF%E8%BF%AA%C2%B7%E8%90%A8%E8%8E%AB%E5%B0%94)（Adi Shamir）和[伦纳德·阿德曼](https://baike.baidu.com/item/%E4%BC%A6%E7%BA%B3%E5%BE%B7%C2%B7%E9%98%BF%E5%BE%B7%E6%9B%BC)（Leonard Adleman）一起提出的。1987年7月首次在美国公布，当时他们三人都在麻省理工学院工作实习。RSA就是他们三人姓氏开头字母拼在一起组成的。

*2: 这一行提示密钥会默认生成到 /root/.ssh/id_rsa文件中，这个规则是和当前执行keygen的用户挂钩的，默认会在当前用户的主目录下创建.ssh的隐藏文件夹，密钥文件就被保存到这个文件夹下。如果没有特别的要求，可以不必输入新的文件，保留默认值就好。

*3: 输入密码，为了避免提取的时候麻烦，这个密码可以不设置直接回车

*4：这一行是说明生成的身份标识已经保存到/root/.ssh/test_rsa文件中了，这里保存的是私钥，会用于后续登陆服务器的身份校验

*5:  这一行说明公钥保存到/root/.ssh/test_rsa.pub文件中了，这个公钥后续会被上传到ssh server所在的服务器。

*6:  这是对指纹的说明，256位的加密指纹已经生成，专用于[root@hadoop01.esrichina.com](mailto:root@hadoop01.esrichina.com) 这台服务器。 这个标识符非常重要，可以理解为为[hadoop01.esrichina.com](http://hadoop01.esrichina.com)服务器root用户生成的专属密钥。后续私钥的提取会从root用户下的.ssh隐藏文件夹中的私钥文件中提取。这就意味着我以root用户生成的公钥，上传到服务器上后，是否能以其它用户（比如hdoop用户）免密登陆服务器呢？答案是no。

### 3，上传客户端公钥到ssh服务器端

```
[root@hadoop01 .ssh]# scp ~/.ssh/id_rsa.pub root@hadoop02.esrichina.com:~/.ssh
[root@hadoop01 .ssh]# scp ~/.ssh/id_rsa.pub root@hadoop03.esrichina.com:~/.ssh
```

scp 是openssh-clients包提供的命令，可以用于在服务器之间拷贝文件。上述命令的意思是：将hadoop01服务器，root用户主目录~ 下的.ssh/id_rsa.pub文件拷贝到目标服务器[hadoop02.esrichina.com](http://hadoop02.esrichina.com): root用户主目录下的.ssh文件夹下。如果目标服务器不存在.ssh文件夹，那可以通过下述命令创建，并分配700权限：

```
[root@hadoop02 ssh]# mkdir ~/.ssh
[root@hadoop02 ssh]# chmod -R 700 ~/.ssh
[root@hadoop03 ssh]# mkdir ~/.ssh
[root@hadoop03 ssh]# chmod -R 700 ~/.ssh
```

### 4，将公钥复制到authorized_keys

```
[root@hadoop02 .ssh]# cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
[root@hadoop03 .ssh]# cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

### 5，验证成果

```
[root@hadoop01 .ssh]# ssh root@hadoop02.esrichina.com                  
Last login: Wed Jan 10 08:49:16 2018
```

如果你看到上述成果，不用输入密码即可登陆，那就说明成功啦。

### 6，坑

如果在同一台ssh客户端机器上创建多次密钥，那免密配置可能不会成功，无论怎么折腾，都会提示你输入密码登陆。

解决办法：

当存在多个私钥时，可以通过config文件明确为连接的ssh server指定需要匹配的私钥。具体操作如下：

```
[root@hadoop01 .ssh]# vim config
```

在打开的文件中填入：

```
Host hadoop02.esrichina.com                  *1
​        IdentityFile ~/.ssh/test_rsa         *2
​        User root                            *3
```

*1：指定要连接的ssh server的host name;  

*2: 配置IdentityFile，指定配对的私钥； 

*3: 设置登录ssh server的用户

