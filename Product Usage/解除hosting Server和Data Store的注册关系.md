# 解除Hosting Server和Data Store的注册关系 #


在ArcGIS Enterprise的部署中，每一个ArcGIS Data Store安装后都需要注册ArcGIS Server，建立和站点的联系，这个过程中DataStore完成了建库（可能是关系型数据库，可能是切片缓存库，也可能是时空大数据库），Server从普通的ArcGIS Server升级为hosting Server。建立关系的过程很美好，但是总有那么一个理由，需要我们解除关系来恢复各自独立。

解除hosting Server和Data Store的注册关系可以从两个方向入手。如果是因为Data Store意外故障，我们就可以从Server端解除对Data Store的注册。如果是因为Server端故障，比如重新安装了Server， 我们就需要从Data Store端解除对原有Server的绑定。

## 1 从Server端解除注册    

从Server端解除Data Store 的注册可以参照如下流程：  

1） 登录Server admin 管理站点；  

![登录Server admin](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系01.png)   


2）导航到要解除的data item 信息页，拷贝Item Path；  
  
![拷贝Item Path](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系02.png)  

3)导航到unregisterItem页面，输入Item path, 点击unregister Item按钮发送反注册请求。

![反注册Data Item](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系03.png)  


4）验证结果。  


![验证结果](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系04.png)   



## 2 从Data Store端解除注册  
在Data Store端解除Data Store和Server的绑定可以通过unregisterdatastore脚本工具来实现，这个工具位于“\<ArcGIS Data Store installation directory\>\datastore\tools”目录下。  

解除流程：  

1）检查DataStore中当前已经注册的库：  

![检查注册库](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系05.png)    
 

从上图中可以看出当前测试的Data Store中注册了关系型和切片缓存型数据库。  
 

2）打开命令行工具，cd到 \<ArcGIS Data Store installation directory\>\datastore\tools目录下,参照下图执行解除操作：  
  
![命令解除](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/解除hostingServer和DataStore的注册关系06.png)    


这个工具非常简单，只有一个关键参数--store， 顾名思义就是指定解除哪个库，在这个测试中我解除的是切片缓存库。按照确认提示，输入yes，当看到"Operation completed successfully"，就表示解除成功啦。

上面的过程是在故障的假设下，无论从Server端还是从Data Store端都可以成功解除绑定，解除的过程并不要求对方一定有效，也就是不会相互校验有效性，这样设计，确保当任意一方出现意外状况时，不至于死锁导致双方无法解除关系。反过来，如果是在正常运行的系统中测试这个功能，那无论从任意一方反注册，双方都会同时解除。大数据集群环境下的解除过程，后面测试后我会再更新。



  



