#如何为windows 文件共享开启”盘符$”访问权限
###【问题描述】
通过samba远程更新服务器资源，如果需要使用c$, d$类似这种盘符的共享接口，可能会遇到“拒绝访问”的错误。

![错误截图](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/如何为windows 文件共享开启”盘符$”访问权限01.png)  
￼
###【问题分析】
导致问题出现的原因是微软系统默认开启了一个非常小众的安全策略叫做“UAC 远程限制”，它会为本地用户账户或Windows账户过滤访问token. 这将限制局域网内用户以管理员用户通过“盘符$”的方式访问共享目录。

###【解决办法】
在运行中，输入regedits，打开注册表，修改HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System
将FilterAdministratorToken的键值设置为0，即可关闭这一安全策略。

![修改截图](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/如何为windows 文件共享开启”盘符$”访问权限02.png) 
￼
