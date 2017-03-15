#修复iOS Xcode 8 Error : Protocol not available, dumping backtrace[duplicate]

在基于Xcode8.2新建工程时，可能会碰到如下错误：

![错误截图](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/修复iOS Xcode 8 Error 02.png)



###修复办法：

1. 在Xcode 菜单中，选择Product > Scheme > Edit Scheme

2. 添加环境变量：OS_ACTIVITY_MODE 值为 disable

![示例截图](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/修复iOS Xcode 8 Error 01.png)  


3. 点击Close按钮，关闭窗口后，重新运行工程，你会发现错误解除。




