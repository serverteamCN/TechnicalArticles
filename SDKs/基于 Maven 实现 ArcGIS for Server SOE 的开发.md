#基于 Maven 实现 ArcGIS for Server SOE 的开发
===================


**基于Maven实现ArcGIS for Server SOE的开发**这篇文档是基于用户的特定需求进行测试后整理的，着重于开发环境的搭建以及基于soepackager实现soe的导出。不过，我个人更加推荐用Eclipse作为开发平台，以方便使用ArcGIS提供的Plugin for Eclipse基于默认模板完成从SOE开发到导出的全过程。


## 1 准备

### 1.1 安装和配置JDK
#### 1.1.1 安装 JDK
下载和安装jdk-8u121-windows-x64.exe。
#### 1.1.2 配置 JDK
在Windows系统环境变量下新建 **JAVA_HOME**变量，设置为java安装路径如C:\java\jdk；
新建**CLASSPATH**变量，设置为.;%JAVA_HOME%\lib\dt.jar;%JAVA_HOME%\lib\tools.jar；
编辑**Path**变量，添加%JAVA_HOME%\bin。

![Windows上JDK配置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8AJDK%E9%85%8D%E7%BD%AE.png)

 >**注意：**
 > 注意JDK的版本和ArcGIS内置JRE版本的一致性，避免利用soepackager打包时报 **Unsupported major.minor version 52.0**的错误。

### 1.2 安装和配置Maven
#### 1.2.1 安装Maven
下载apache-maven-3.3.9-bin.zip并解压。
#### 1.2.2 配置Maven
在windows系统环境变量下新建**MAVEN_HOME**变量，设置为**2.1**中的Maven路径，如E:\apache-maven-3.3.9；
编辑**Path**变量，添加MAVEN_HOME\bin。
![Windows上maven配置](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/Windows%E4%B8%8AMaven%E9%85%8D%E7%BD%AE.png)
#### 1.2.3 验证Maven
打开windows命令窗口，运行mvn -v，如果出现如下信息，则说明Maven安装成功。

	C:\Users\Administrator>mvn -v
	    Apache Maven 3.3.9 (bb52d8502b132ec0a5a3f4c09453c07478323dc5; 2015-11-11T00:41:47+08:00)
	    Maven home: E:\development\apache-maven-3.3.9
	    Java version: 1.8.0_121, vendor: Oracle Corporation
	    Java home: C:\java\jdk\jre
	    Default locale: zh_CN, platform encoding: GBK
	    OS name: "windows 10", version: "10.0", arch: "amd64", family: "dos"

#### 1.2.4 修改Maven本地存储库位置
取消注释%MAVEN_HOME%\conf\settings.xml文件中的localRepository这一小节，并修改参数值。

	  <!-- localRepository
	   | The path to the local repository maven will use to store artifacts.
	   |
	   | Default: ${user.home}/.m2/repository
	   -->
	  <localRepository>E:\local-repo-for-maven</localRepository>

#### 1.2.5 运行**mvn help:system**
运行mvn help:system命令，一方面打印所有Java系统变量和环境变量，另一方面从远程资源库中的jar包下载至**2.4**中设置的本地存储库中。

    [INFO] ------------------------------------------------------------------------
	[INFO] BUILD SUCCESS
	[INFO] ------------------------------------------------------------------------
	[INFO] Total time: 02:43 min
	[INFO] Finished at: 2017-02-28T18:34:46+08:00
	[INFO] Final Memory: 12M/150M
	[INFO] ------------------------------------------------------------------------

出现如上信息，说明运行成功。



## 2 SOE开发

### 2.1 安装ArcGIS Objects包到Maven本地存储库
将ArcGIS Objects核心包即arcobjects.jar安装到Maven本地存储库，方便后面的开发过程引用。

    E:\>mvn install:install-file -DgroupId=com.esri.sdk.ao -DartifactId=arcobjects -Dversion=10.5 -Dpackaging=jar -Dfile=E:\arcobjects.jar
出现如下信息，说明安装成功

	[INFO] Installing E:\arcobjects.jar to E:\local-repo-for-maven\com\esri\sdk\ao\arcobjects\10.5\arcobjects-10.5.jar
	[INFO] Installing C:\Users\ADMINI~1\AppData\Local\Temp\mvninstall7772689279552139840.pom to E:\local-repo-for-maven\com\esri\sdk\ao\arcobjects\10.5\arcobjects-10.5.pom
	[INFO] ------------------------------------------------------------------------
	[INFO] BUILD SUCCESS
	[INFO] ------------------------------------------------------------------------
	[INFO] Total time: 22.945 s
	[INFO] Finished at: 2017-02-28T18:52:59+08:00
	[INFO] Final Memory: 9M/149M
	[INFO] ------------------------------------------------------------------------


### 2.2 建立SOE项目

    E:\mvn-reprojects>mvn archetype:generate -DgroupId=com.esrichina.simplerestsoe -DartifactId=simplerestsoe -Dversion=1.0 -DarchetypeArtifactId=maven-archetype-quickstart -DinteractiveMode=false
看到如下信息，说明Java项目构建成功。

    [INFO] BUILD SUCCESS
	[INFO] ------------------------------------------------------------------------
	[INFO] Total time: 01:07 min
	[INFO] Finished at: 2017-02-28T19:19:34+08:00
	[INFO] Final Memory: 14M/216M
	[INFO] ------------------------------------------------------------------------

### 2.2 编辑SOE项目
参照Sample中的[Simple REST SOE](http://desktop.arcgis.com/en/arcobjects/latest/java/#ed8936e3-55d1-460b-acd4-ef603a0932f8.htm)编辑App.java文件，构建您的第一个SOE应用。

### 2.3 编译SOE项目
1 编辑pom.xml文件，添加项目所依赖的第三库jar包。

    <dependency>
      <groupId>com.esri.sdk.ao</groupId>
      <artifactId>arcobjects</artifactId>
      <version>10.5</version>
    </dependency>
 >**注意：**
 > 这里添加的groupId、arctifactId和version等参数要和步骤**2.4**中添加至本地存储库中的信息保持一致。

2 进入pom.xml所在的文件夹编译项目。

    E:\mvn-reprojects\simplerestsoe>mvn compile

出现如下信息，说明项目编译成功。

    [INFO] Compiling 1 source file to E:\mvn-reprojects\simplerestsoe\target\classes
	[INFO] ------------------------------------------------------------------------
	[INFO] BUILD SUCCESS
	[INFO] ------------------------------------------------------------------------
	[INFO] Total time: 50.854 s
	[INFO] Finished at: 2017-02-28T19:34:56+08:00
	[INFO] Final Memory: 19M/243M
	[INFO] ------------------------------------------------------------------------

### 2.3 打包SOE项目

    E:\mvn-reprojects\simplerestsoe>mvn package
出现如下信息，说明项目打包成功。

    [INFO] Building jar: E:\mvn-reprojects\simplerestsoe\target\simplerestsoe-1.0.jar
	[INFO] ------------------------------------------------------------------------
	[INFO] BUILD SUCCESS
	[INFO] ------------------------------------------------------------------------
	[INFO] Total time: 35.121 s
	[INFO] Finished at: 2017-02-28T19:39:50+08:00
	[INFO] Final Memory: 20M/212M
	[INFO] ------------------------------------------------------------------------

## 3 调用soepackager打包SOE项目
### 3.1 修改 soepackager.bat
根据测试，soepackager.bat文件中的JAVA_HOME、soe_jar_file、output_folder和jdkpath三个变量存在问题，将导致soepackager运行失败。
请参照如下设置进行修改
###3.2 运行soepackager.bat

    C:\Program Files (x86)\ArcGIS\DeveloperKit10.5\java\tools\soepackager>soepackager.bat -p E:\mvn-reprojects\simplerestsoe\target\simplerestsoe-1.0.jar -o E:\mvn-reprojects\simplerestsoe -j C:\java\jdk

出现如下信息且E:\mvn-reprojects\simplerestsoe路径下出现simplerestsoe-1.0.soe文件，说明SOE项目打包成功。

    Found SOE with Class Name :com.esrichina.simplerestsoe.App



## 4 部署SOE


1 访问ArcGIS for Server Manager，导航至Site -> Extensions，点击Add Extension按钮，浏览至simplerestsoe-1.0.soe并添加。

![添加SOE扩展](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EMaven%E5%AE%9E%E7%8E%B0ArcGISforServerSOE%E7%9A%84%E5%BC%80%E5%8F%910.PNG)

2 对SampleWorldCities服务启用这一SOE功能，保存并重启。

![启用SOE扩展功能](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EMaven%E5%AE%9E%E7%8E%B0ArcGISforServerSOE%E7%9A%84%E5%BC%80%E5%8F%911.PNG)

3 访问SampleWorldCitie的REST服务页面，点击页面底端**Supported Extensions:App**。

![导航至REST页面上的SOE功能](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EMaven%E5%AE%9E%E7%8E%B0ArcGISforServerSOE%E7%9A%84%E5%BC%80%E5%8F%912.PNG)

4 点击 **Supported Operations：getLayerCountByType**，输入type为feature，获得结果**count:3**，说明SOE部署且运行成功。

![运行和验证SOE功能](https://github.com/serverteamCN/TechnicalArticles/blob/master/pictures/%E5%9F%BA%E4%BA%8EMaven%E5%AE%9E%E7%8E%B0ArcGISforServerSOE%E7%9A%84%E5%BC%80%E5%8F%913.PNG)
