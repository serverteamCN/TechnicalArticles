# Windows上安装ArcGIS Enterprise——以 Windows Server 2012 R2上安装 ArcGIS 10.5为例 #

    目录：
	1 安装前准备
		1.1 修改机器名
    	1.2 安装和配置IIS
			1.2.1 安装IIS
			1.2.2 创建和配置自签名证书
			1.2.3 对IIS启用https
		1.3 准备ArcGIS Enterprise安装所需的软件包
	2 安装和配置 ArcGIS for Server
		2.1 安装ArcGIS for Server
		2.2 配置ArcGIS for Server
	3 安装和配置 ArcGIS Data Store
		3.1 安装ArcGIS Data Store
		3.2 配置ArcGIS Data Store
    4 安装和配置 Portal for ArcGIS
		4.1 安装 Portal for ArcGIS
		4.2 配置 Portal for ArcGIS
    5 安装和配置 ArcGIS Web Adaptor
		5.1	安装 ArcGIS Web Adaptor
		5.2 用名为arcgis的Web Adaptor配置Portal for ArcGIS
		5.3 用名为server的Web Adaptor配置Portal for ArcGIS
    6 实现Portal for ArcGIS和ArcGIS for Server的联合和托管


本文以Windows Server 2012 R2上安装ArcGIS Enterprise 10.5为例，详细描述单机环境下安装ArcGIS Enterprise的完整过程。

## 1 安装前准备 ##

### 1.1 修改机器名 ###

ArcGIS for Enterprise的部署要求计算机名是完全限定域名的形式。

如果您的计算机隶属于域环境，则直接采用您现有的完全限定域名的形式即可。非域环境下则可通过设置DNS后缀来实现这一形式。具体步骤如下：

1）打开**系统属性**对话框,点击**更改**

2）在弹出的**计算机名/域更改**对话框中点击**其他(M)...**

3）在弹出的**DNS后缀和NetBIOS计算机名**对话框中，对**此计算机的主DNS后缀(P):**任意设置一个自定义域名

![非域环境下设置DNS后缀获取完全限定域名的机器名](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2001.png)

### 1.2 安装和配置IIS ###

#### 1.2.1 安装IIS ####

1）打开**服务器管理**，点击**添加角色和功能**

2）点击**下一步**

3）在**选择安装类型**面板上，选择**基于角色或基于功能的安装**,点击**下一步**

4）点击**下一步**

5）在**选择服务器角色**面板上，选中**Web服务器(IIS)**,并在弹出的**添加角色和功能向导**对话框上，点击**添加功能**，点击**下一步**

![选中安装 Web服务器（IIS）](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2002.png)

6）依次点击**下一步**直至进入**确认安装所选内容**面板，点击**安装**

![确认Web服务器（IIS）的安装](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2003.png)

#### 1.2.2 创建和配置自签名证书 ####

1）打开**服务器管理**，点击**工具** -> **Internet Information Services(IIS)管理器**

2）在**Internet Information Services(IIS)管理器**界面上，选中**连接**窗格中的计算机名

3）在**功能视图**中双击**服务器证书**

![在功能视图上点击服务器证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2004.png)

4）在**服务器证书**窗格右侧的**操作**窗口中，点击**创建自签名证书**

![点击创建自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2005.png)

5）在**指定友好名称**面板上任意指定一个具有标识性的名称如server128,并点击**确定**

![指定自签名证书的名字](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2006.png)

6）步骤5中创建的自签名证书列在**服务器证书**窗格中

![创建好的证书列出在服务器证书窗口中](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2007.png)

#### 1.2.3 对IIS启用https ####

1）在**Internet Information Services(IIS)管理器**界面上，依次点击**连接**窗格中的计算机名-> **网站**->**Default Web Site**，点击右侧窗格中的**绑定...**

![单击操作中的绑定以绑定自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2008.png)

2）在弹出的**网站绑定**对话框中，点击**添加**打开**添加网站绑定**对话框

![对https绑定自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2009.png)

3）在**类型**下拉列表中选择**https**，对**SSL证书(F):**选择步骤**1.2.2**中创建的自签名证书server128

![绑定自签名证书](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2010.png)

4）点击**确定**完成IIS上启用https的过程。

5）依次点击**下一步**直至进入**确认安装所选内容**面板，点击**安装**

这样，您就可通过https://【完全限定的计算机名】成功访问IIS了。

![自签名证书在IIS级别配置完毕](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2011.png)

### 1.3 准备ArcGIS Enterprise安装所需的软件包 ###

ArcGIS Enterprise的部署需要安装 ArcGIS for Server、ArcGIS Data Store、Portal for ArcGIS和Web Adaptor四个组件。这里我们的软件包准备如下：

![准备安装所需软件包](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2012.png)

## 2 安装和配置 ArcGIS for Server ##

### 2.1 安装 ArcGIS for Server ###

1）双击步骤**1.3**中准备的ArcGIS_Server_Windows_105_154004.exe开始安装包的提取

提取完毕后，安装界面上默认勾选**Launch the setup program**，点击**close**即进入ArcGIS for Server的安装。

2）点击**Next**,在**License Agreement**安装界面上选中**I accept the license agreement**

![同意许可认证协议](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2013.png)

3）依次点击**Next**默认安装路径。如果C盘空间较小，建议点击**Select Features**和**Python Destination Folder**两个安装界面上的**Change**按钮以修改默认安装路径

![指定安装路径](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2014.png)

4）在**Specify ArcGIS Server Account**安装界面上，指定ArcGIS for Server账户

![指定ArcGIS for Server账户](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2015.png)

这是一个操作系统级别的安装账户，ArcGIS for Server的所有进程都以此账户身份运行。您可通过指定一个新的账户名和密码在操作系统上新建这一账户；也可直接使用一个现有的操作系统账户。

5）依次点击**Next**直至**Ready to Install the Program**界面，点击**Install**至安装完毕

![准备安装](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2016.png)

6）点击**Finish**通过**Software Authorization Wizard**完成软件的在线或离线授权。也可点击**Software Authorization Wizard**界面上的**取消**稍后进行软件授权

软件授权完毕后，浏览器自动打开ArcGIS for Server的站点创建界面。您也可通过在浏览器中输入https://server128.esrichina.com:6443/arcgis/manager打开站点创建界面。

### 2.2 配置 ArcGIS for Server ###

1）在自动弹出的ArcGIS Server Manager界面上，点击**继续浏览此网站(不推荐)**

2）在**ArcGIS Server安装向导**界面上，点击**创建新站点**

3）在**主站点管理员账户**界面上，输入主站点管理员账户的用户名和密码

这是一个应用程序级别的账户，而不是操作系统级别的账户，您可根据需要自行创建。

4）在**指定根服务器目录和配置存储**界面上为ArcGIS for Server的config-store和directories指定存储位置

5）点击**完成**直至站点创建完毕

![完成ArcGIS for Server站点创建的完整过程](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2017.gif)

6）站点创建完毕后，即可通过输入主站点管理员的用户名和密码登录ArcGIS Server Manager

![站点创建完毕登录ArcGIS Server Manager](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2018.png)

## 3 安装和配置 ArcGIS Data Store ##

### 3.1 安装 ArcGIS Data Store ###

1）双击步骤**1.3**中准备的ArcGIS_DataStore_Windows_105_154006.exe开始安装包的提取

提取完毕后，安装界面上默认勾选**Launch the setup program**，点击**close**即进入ArcGIS Data Store的安装。

2）点击**Next**,在**License Agreement**安装界面上选中**I accept the license agreement**

3）点击**Next**默认安装路径。如果C盘空间较小，建议点击**Select Features**安装界面上的**Change**按钮以修改默认安装路径

4）在**Specify ArcGIS Data Store Account**安装界面上，指定ArcGIS Data Store账户

![指定ArcGIS Data Store账户](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2020.png)

这是一个操作系统级别的安装账户，ArcGIS Data Store的所有进程都以此账户身份运行。您可通过指定一个新的账户名和密码在操作系统上新建这一账户；也可直接使用一个现有的操作系统账户。这一账户可与ArcGIS for Server账户相同，也可根据需要设置其他账户。

5）依次点击**Next**直至**Ready to Install the Program**界面，点击**Install**至安装完毕

安装完毕后，浏览器自动打开ArcGIS Data Store的配置页面。您也可通过在浏览器中输入https://server128.esrichina.com:2443/arcgis/datastore打开这一配置页面。

### 3.2 配置 ArcGIS Data Store ###

1）在自动弹出的ArcGIS Data Store界面上，点击**继续浏览此网站(不推荐)**

2）在**Data Store配置向导**界面上，根据提示输入步骤**2.2**中创建的ArcGIS for Server站点的地址，主站点管理员的用户名和密码，点击**下一步**

![指定ArcGIS Data Store要配置的目标站点](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2021.png)

3）在**指定内容目录**界面上，指定ArcGIS Data Store配置内容、日志以及备份文件等的存储位置，点击**下一步**

![指定ArcGIS Data Store 内容目录的位置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2022.png)

4）在**ArcGIS Data Store类型**界面指定您要配置的Data Store类型：关系、切片缓存和时空。可根据需要进行选择。默认情况下，只需选择**关系**类型，点击**下一步**

![指定配置的 Data Store 的类型](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2023.png)

5）确认配置信息无误，点击**完成**直至Data Store配置完毕。

![确认 Data Store 配置信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2024.png)

## 4 安装和配置 Portal for ArcGIS ##

### 4.1 安装 Portal for ArcGIS ###

1）双击步骤**1.3**中准备的Portal_for_ArcGIS_Windows_105_154005.exe开始安装包的提取

提取完毕后，安装界面上默认勾选**Launch the setup program**，点击**close**即进入Portal for ArcGIS的安装。

2）点击**Next**,在**License Agreement**安装界面上选中**I accept the license agreement**

3）点击**Next**默认安装路径。如果C盘空间较小，建议点击**Select Features**和**Specify the Portal for ArcGIS directory**安装界面上的**Change**按钮以修改默认安装路径

4）在**Specify the Portal for ArcGIS Account**安装界面上，指定Portal for ArcGIS账户

![指定Portal for ArcGIS账户](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2025.png)

这是一个操作系统级别的安装账户，Portal for ArcGIS的所有进程都以此账户身份运行。您可通过指定一个新的账户名和密码在操作系统上新建这一账户；也可直接使用一个现有的操作系统账户。这一账户可与ArcGIS for Server账户相同，也可根据需要设置其他账户。

5）依次点击**Next**，点击**Install**至安装完毕

6）点击**Finish**通过**Software Authorization Wizard**完成软件的在线或离线授权。也可点击**Software Authorization Wizard**界面上的**取消**稍后进行软件授权

软件授权完毕后，浏览器自动打开Portal for ArcGIS的配置界面。您也可通过在浏览器中输入https://server128.esrichina.com:7443/arcgis/home/createadmin.html打开**Create Or Join a Portal**这一配置页面
。

### 4.2 配置 Portal for ArcGIS ###

1）在自动弹出的Portal for ArcGIS界面上，点击**继续浏览此网站(不推荐)**

2）在**Create or Join a Portal**界面上，点击**CREATE NEW PORTAL**

![开始创建Portal for ArcGIS站点](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2026.png)

3）在**Create a New Portal**界面上，指定Portal for ArcGIS的初始管理员账户的信息，并配置内容目录的位置，点击**CREATE**

![指定Portal创建的各项配置信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2027.png)

4）在弹出的**Account Created**界面上点击**确定**完成Portal for ArcGIS的配置。

![账户创建完毕](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2028.png)

## 5 安装和配置 ArcGIS Web Adaptor ##
### 5.1 安装 ArcGIS Web Adaptor ###

1）双击步骤**1.3**中准备的Web_Adaptor_for_Microsoft_IIS_105_154007.exe开始安装包的提取

提取完毕后，安装界面上默认勾选**Launch the setup program**，点击**close**即进入Portal for ArcGIS的安装。

2）在**IIS requirements verification**安装界面上，点击**I Agree**自动安装缺失的IIS组件

![安装缺失的IIS组件](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2030.png)

3）点击**Next**,在**License Agreement**安装界面上选中**I accept the license agreement**

4）依次点击**Next**直至**New Virtual Directory**界面，指定ArcGIS Web Adaptor的名字。默然是arcgis，点击**Next**

![指定Web Adaptor的名字](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2031.png)

5）点击**Install**直至完成

浏览器自动打开Web Adaptor配置页面http://localhost/arcgis/webadaptor。

重复上述过程以安装一个名为 Server 的 Web Adaptor，用于ArcGIS for Server的配置。

![指定用于配置 ArcGIS for Server的Web Adaptor的名字](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2032.png)

### 5.2 用名为arcgis的Web Adaptor配置Portal for ArcGIS ###

1）在自动打开的浏览器中，对**要使用Web Adaptor配置哪种产品**选择**Portal for ArcGIS**以实现Portal for ArcGIS的配置，点击**下一步**

![选择配置产品的类别](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2033.png)

2）输入步骤**4.2**配置的Portal for ArcGIS门户URL和初始化管理员的用户名和密码，点击**配置**完成对于Portal for ArcGIS的配置

![输入配置Portal for ArcGIS所需填入的信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2034.png)

![配置Portal for ArcGIS完毕](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2035.png)

### 5.3 用名为server的Web Adaptor配置ArcGIS for Server ###

1）在自动打开的浏览器中，对**要使用Web Adaptor配置哪种产品**选择**ArcGIS Server**以实现ArcGIS for Server的配置，点击**下一步**

2）输入步骤**3.2**配置的ArcGIS for Server站点URL和主站点管理员的用户名和密码，点击**配置**完成对于ArcGIS for Server的配置

![输入配置ArcGIS for Server所需填入的信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2036.png)

![配置ArcGIS for Server完毕](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2037.png)

## 6 实现Portal for ArcGIS和ArcGIS for Server的联合和托管 ##

1）在浏览器中输入步骤**5.2**中获得的Portal for ArcGIS门户应用程序URL，点击**Sign In**

![打开Portal for ArcGIS开始配置联合和托管](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2038.png)

2）输入Portal for ArcGIS初始化管理员账户的用户名和密码，点击**SIGN IN**进行登录

![输入Portal初始化管理员的用户名和密码以登录](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2039.png)

3）页面自动跳转至**My Organization**选项卡下，点击**EDIT SETTING**

![点击编辑按钮开始设置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2040.png)

4）在左侧选项卡中选中**Servers**,点击右侧面板中的**ADD SERVER**

![点击 ADD SERVER开始添加要联合的ArcGIS for Server](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2041.png)

5）在弹出的**Add ArcGIS Server**界面上，根据提示依次输入ArcGIS for Server的REST服务目录地址、ArcGIS for Server管理页面的地址、ArcGIS for Server主站点管理员的用户名和密码，点击**ADD**，即实现ArcGIS for Server和Portal for ArcGIS的联合

![输入要联合的ArcGIS for Server的信息](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2042.png)

6）在右侧面板的**Hosting Server**下的下拉列表中选中步骤**5）**中添加的Server，点击**SAVE**，即实现ArcGIS for Server和Portal for ArcGIS的托管

![配置 ArcGIS for Server的托管](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8A%E5%AE%89%E8%A3%85ArcGIS%20Enterprise%2043.png)


至此，ArcGIS Enterprise在Windows单机上的安装完毕。