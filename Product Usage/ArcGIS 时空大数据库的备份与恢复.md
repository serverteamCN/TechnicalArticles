# ArcGIS时空大数据库的备份与恢复 #


在ArcGIS Enterprise 产品中最闪亮的特性之一就是支持时空大数据的分析和展示。时空大数据在整个平台中存储在ArcGIS Datastore 的时空大数据库（spatiotemporal datastore）中。这个时空大数据库是否安全？是否能应对各种可能出现的比如数据库崩溃，系统崩溃等等意外？如果因为项目需要，想从一台服务器上迁移时空大数据库到另外一台服务器上，数据该如何迁移？事实上，Esri提供了现成的备份和迁移工具，可以帮助我们实现灾备和平滑迁移数据。这篇文章我们将重点聚焦在时空大数据库的备份和恢复技术实战上。

备份是为了应对灾难，比如服务器崩溃，发生自然灾害机房损毁等等，如果我们将备份文件存储在同一台服务器上，显然在服务器崩溃，系统失灵的状态下，备份文件也将损毁，备份就失去了它存在的意义。在系统设计时，要根据安全需求妥善设置备份存储位置。对于时空大数据库的备份，DataStore强制要求这个备份位置必须是共享目录，最好存放在远程服务器上。备份时空大数据库之前，最重要的工作就是注册一个安全的，共享的备份位置给ArcGIS Data Store用于存放备份文件。
  



## 1 定义备份位置 
### 1.1 备份位置要求
－ 在远程服务器上创建文件夹，并共享，添加Data Store Service运行用户到贡献权限列表；  

![分配共享权限](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧05.png)

－ 确保Data Store Service运行用户对共享文件夹有完全控制权限；  

![分配访问权限](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧06.png)

－ 确保所有时空大数据库所在服务器都能访问共享目录；  

－ 确保有足够的存储空间用以保存备份文件，整个时空大数据库集群的数据都会保存到备份目录；  

－到hosting server 的admin管理器中检测大数据集群的健康状态。  

![分配访问权限](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧07.png)
  
  
### 1.2 设置备份位置  
设置时空大数据库的备份位置可以通过configurebackuplocation脚本工具来实现，这个工具位于“\<ArcGIS Data Store installation directory\>\datastore\tools”目录下。  

工具语法：  

changebackuplocation <new directory path> [--is-shared-folder <true|false>] [--keep-old-backups <true|false>]  


\<new directory path\>:  必选参数，对于时空大数据库，这儿需要输入的是共享目录（UNC）；    
[--is-shared-folder <true|false>]: 需要告诉工具这个文件夹是否是共享的，显然需要输入true;  
[--keep-old-backups <true|false>]： 如果想要从原有备份目录迁移备份文件到新目录，指定值为true。  

参照下图执行命令：  

![创建备份目录](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧01.png)  

在命令执行过程中有一行提示，翻译过来：  

       “你正在尝试改变data store的备份位置。对于关系型数据库，现有的备份文件会自动拷贝到新的位置，这可能需要花费一点儿时间。对于时空大数据库，服务可能会重启。一旦开启请不要中断这个过程。”  

*这个提示非常重要，告诉我们在更改时空大数据库备份位置时，datastore服务可能需要重启，这就意味着在更改备份目录位置时尽量不要有写入数据业务执行，这可能会导致操作失败。最推荐的操作是一旦建好时空大数据库，在执行任何业务之前，首先执行备份目录设置操作。


## 2 手动创建备份  
  
创建时空大数据库的备份可以通过backupdatastore 工具执行，这个工具位于\<ArcGIS Data Store installation directory\>\datastore\tools目录下。 
 
工具语法：  
 
backupdatastore [<backup_name>] --store {relational | tilecache | spatiotemporal}

backup_name : 指定备份名，这个参数也可以省略，如果不指定，工具会自动生成一个以datastorename-timestamp为规则的名字。  

--store ： 指定要备份的datastore库，这里选择spatiotemporal。

参照下图执行命令：

![创建备份库](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧02.png)

对于时空大数据库，备份的机制是在首次备份时，备份全部的数据，也就是“完整备份”。由于时空大数据库本身的数据量可能是海量的，每次备份全部数据就太浪费了，后续执行备份操作时工具会自动备份上次执行备份工具以来的增量数据。  

## 3 恢复时空大数据库  
 
一旦出现任何意外，引发时空大数据库集群崩溃，我们就可以使用之前的备份文件恢复时空大数据库。
  
### 3.1 恢复前的准备工作  


恢复前的检查工作就是要检测hosting server中是否仍然保留了原来的大数据库连接：如果有，要反注册掉数据库，详细流程参照：[反注册DataItem](https://github.com/serverteamCN/TechnicalArticles/blob/master/Product%20Usage/解除hosting%20Server和Data%20Store的注册关系.md)

为了存储更多数据，时空大数据库通常会是一个集群，要注意，备份文件是存储了集群中所有服务器上的时空大数据，在恢复的时候，如果把所有数据恢复到单机上，可能会由于资源不足而导致失败。从10.5.1开始，时空大数据的恢复支持分阶段执行，以避免单机内存和硬盘空间不足的问题。

### 3.2 恢复工具  
恢复时空大数据库，可以通过restoredatabase 工具来实现，这个工具位于\<ArcGIS Data Store installation directory\>\datastore\tools目录下 。  

工具语法：  

restoredatastore [operations]  

支持的操作（operations）：  
	•	[--store{relational | tileCache | spatiotemporal}]  ： 指定DataStore的库类型；  
	•	[--target {most-recent | <yyy-mm-dd-hh:mm:ss> | <name of backup file>}]: 指定恢复是按照最近，指定时间点，还是按照备份文件名来恢复；  
	•	[--source-loc <location of source backup files>]: 指定备份文件所在位置；  
	•	[--bound {true | false}] ： 指定是否保持datastore注册GIS Server site的关系，默认值为true；  
	•	[--data-dir <new data store directory>] 指定恢复服务器上新的datastore目录；  
	•	[--server-url <ArcGIS Server URL registered with data store>] : 这个参数和bound参数直接关联，如果绑定为true，必须要指定注册data store的GIS Server站点的url。  
	•	[--server-admin <user name of ArcGIS Server admin>]: 这个参数和bound参数直接关联，如果绑定为true，必须要指定server站点的管理员用户名；  
	•	[--server-password <password of ArcGIS Server admin>]: 这个参数和bound参数直接关联，如果绑定为true，必须要指定server站点的管理员密码；  
	•	[--loaddata {true | false}]: 这是仅用于时空大数据库的参数。指定是否在恢复时加载数据到datastore。设定这个值为false，数据不会拷贝，仅会在这个阶段恢复数据库的scheme。在之后将其它大数据库服务器添加到集群后，可以再次运行工具，将这个选项设为true，来同时恢复数据到整个集群服务器。默认这个值为 true。  
	•	[--prompt {yes | no}]：指定是否显示提示。  

参照下图执行命令：

![恢复时空库](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/ArcGIS时空大数据库备份与恢复技巧03.png)

### 3.3 恢复流程
#### 3.3.1 恢复小数据规模的时空大数据库  

对于小数据规模的时空大数据库，如果新装的单台Data Store机器可以承载之前集群中的全部数据，参照以下流程恢复：  

1）在新的服务器上安装ArcGIS Data Store，不要执行配置hosting Server的操作；  
2）以管理员身份运行命令行工具，执行上述的恢复工具；  
3）在其它服务器上安装ArcGIS Data Store， 安装后分别按照配置向导执行对hosting Server的配置, 这个过程可以理解为将其它的时空大数据库重新加入集群。

#### 3.3.2 恢复超大数据的时空大数据库  

前面我提到了10.5.1支持分阶段恢复超大数据的时空大数据库，这个过程是通过参数—loaddata 来控制的,如果为false，表示数据先不加载，具体操作流程： 
 
1）在新的服务器上安装ArcGIS Data Store，不要执行配置hosting Server的操作；  
2）以管理员身份运行命令行工具，执行上述的恢复工具，指定—loaddata 为false；  
3）在其它服务器上安装ArcGIS Data Store， 安装后分别按照配置向导执行对hosting Server的配置, 这个过程可以理解为将其它的时空大数据库重新加入集群。  
4) 再次运行restoredatastore工具，不要再指定—loaddata参数，这时会按默认配置跨所有的时空大数据机器分发数据。  
