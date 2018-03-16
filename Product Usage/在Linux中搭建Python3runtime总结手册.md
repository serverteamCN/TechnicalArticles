# 背景： #
Esri提供了arcpy包，可以通过Python实现以下功能：实现地理数据分析，数据转换，数据管理和地图自动化。（参考附件4中arcpy说明连接）

从10.5开始，Esri提供了Linux上的Python 3 runtime，独立于ArcGIS Server安装，方便执行Python脚本，实现调用arcpy。

Anaconda可以实现简化管理丰富的Python包，Esri 也选择了Anaconda来管理分发arcpy包。

# 目标：

在Linux上安装Python3runtime，调用arcpy，进而通过脚本自动化执行GP工具等功能。

# 环境： #

需要安装ArcGIS Server10.5及以上版本的Linux环境。

# 实现： #

## 概要实现步骤： ##

 安装Anaconda--> 安装Python包-->启动Python环境



## 具体实现步骤 （安装流程可以参考附件2）：

1.	将Anaconda安装介质拷贝到linux环境下；

2.	切到ArcGIS  Server账户安装Anaconda，如下：

    ./Anaconda3-5.0.1-Linux-x86_64.sh

    接下来会让安装者确认默认安装路径以及是否将安装路径添加到.bashrc文件中。
    
	此处的默认安装路径是/home/arcgis106/anaconda3，选择将默认安装路径添加到.bashrc的文件中。
 
 

3.	执行source让路径生效，如下：

	source /home/arcgis106/.bashrc 

	测试并确保环境安装完成，如下：

	conda

	注：如果没有错误信息返回，即说明安装完成。

4.	预先生成一个自定义环境，如下:

	
	conda create --name myenv

	注：上述命令实际完成的是在环境路径下生成一个文件夹，
	此处新文件夹是路径是/home/arcgis106/anaconda3/envs/myenv，用于后续安装目标Python包。

5.	在上步新建环境中安装Python3，此处以ArcGIS Server10.6版本为例：

	conda create -c esri -n myenv arcgis-server-10.6-Python
	
	注：此处python3会安装在/home/arcgis106/anaconda3/envs/myenv下。
 
6.	启动环境

	6.1 首先，需要设置ARCGISHOME变量激活运行Python3的conda环境，如下：

	export ARCGISHOME=/home/arcgis106/arcgis/server

	注：需要将/home/arcgis106/arcgis/server替换成实际的ArcGIS Server安装路径。

	6.2 其次，启动环境：
	
	source activate myenv

	注！：6.1与6.2两步顺序不可颠倒，且每次调用arcpy前都要执行，可以参考附件1--Python 3环境激活shell脚本，代替手动执行。

	步骤6.2执行完毕后，确保前面增加了（myenv）字样，如下图：

	![](https://i.imgur.com/ppWC0w9.png)
 
7.	检查Python 3环境安装语句：

	python

	import arcpy

	注：如果环境通过安装检测，说明环境已经准备好，可在Python脚本中调用arcpy。







----------






	可能遇到的问题之一：

	Linux上执行的Python脚本中调用arcpy，执行Python脚本报错：

![](https://i.imgur.com/opLkBw0.png)
 
	解决办法：

	确保环境启动，每次启动环境都要执行：

	export ARCGISHOME=/home/arcgis106/arcgis/server

	source activate myenv


## 附件： ##
1.	Python3环境激活shell脚本，方便实现流程自动化。

 	连接：https://github.com/AlisonGou/demo/blob/master/py3_activate.sh

2.	如何正确配置Python3环境英文原文参考文件- Python_readme.txt

    连接：https://github.com/AlisonGou/demo/blob/master/py3_readme.txt
3. The Python 3 runtime for ArcGIS Server on Linux

	官方帮助文档：
	http://enterprise.arcgis.com/en/server/latest/administer/linux/linux-python.htm


4. 	arcpy 官方帮助文档：

	http://pro.arcgis.com/zh-cn/pro-app/arcpy/get-started/what-is-arcpy-.htm

3.	Anaconda 官网下载地址：https://www.anaconda.com/download/



