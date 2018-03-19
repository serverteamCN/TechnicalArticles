# 文章面向对象： #
需要实现大数据工具自动化调用的使用者。

# 目的： #
ArcGIS 知乎上已经有一些文章，帮助大家认识什么是ArcGIS Python API，如何部署，使用说明等；此文章的重点不同。

这篇文章的主要目的和重点如下：

1.	根据实际工作流，将相关矢量和栅格大数据工具的使用串联（需求）；

2.	使用Python语言，用两种方式实现脚本；对比两种脚本方式，体验ArcGIS Python API的优缺点（实现）。

	脚本的两种实现方式：一，ArcGIS Python API；二，使用Python直接发起rest请求调用GP服务。

# 理解和实现需求： #

## 理解需求： ##

用户实际工作流：气象部门每小时采集了温度数据，以csv格式存储；根据其数据采集点，生成温度插值结果。插值后的结果可以根据需求（比如按照小时）在前端组织起来。

## 实现需求： ##

### **技术概述：** ###

根据实际工作流，技术上实现对应到如下流程（即需要在脚本中实现的自动化流程）：

将csv注册为大数据共享文件（GA）--> 实现CopytoDataStore（GA）--> 执行插值（RA）--> 栅格函数链并保存最终结果

注：GA 是GeoAnalytics的缩写，RA是RasterAnalytics的缩写。

将以上流程简略展开说明如下：

1.	将csv文件注册为大数据共享文件(附件代码不包含此项)；

2.	执行矢量大数据GA CopytoDataStore，生成托管要素图层；

3.	执行栅格大数据RA InterpolatePoints，生成影像插值图层；

4.	执行栅格函数链，处理影像插值图层；栅格函数链包含掩膜，裁剪，拉伸和渲染,将栅格函数链结果发布成为影像服务。

### 具体实现：  ###


#### 脚本实现方法一： 使用ArcGISPythonAPI（需要ArcGIS Python API 1.3/1.4环境）####

调用GA CopytoDatastore 示例代码参考：
https://github.com/AlisonGou/demo/blob/master/GA_pythonapi_copytodatastore.py

调用RA CopytoDatastore 示例代码参考：
https://github.com/AlisonGou/demo/blob/master/RA_pythonapi_interpolatepoints.py

对RA结果实现栅格函数链处理：
https://github.com/AlisonGou/demo/blob/master/rasterchain.py

#### 脚本实现方法二 ： 使用Python提交rest请求调用GP服务（需要python 3.5环境） ####

调用GA CopytoDatastore 示例代码参考：
https://github.com/AlisonGou/demo/blob/master/GA_gpservice_copytodatastore.py

调用RA CopytoDatastore 示例代码参考：
https://github.com/AlisonGou/demo/blob/master/RA_gpservice_interpolatepoints.py

注：如果大家使用开发者工具监控大数据工具执行过程可以观察到，在Portal中执行大数据分析工具的请求逻辑是遵循方法二的。

## 两种方法对比总结： ##
对比两种实现方式的代码可知，方法一中已经将方法二中的逻辑封装好，只需要调用一个方法即可。


### 方法一： ###

简单方便，学习投入的时间精力少；

已经将方法二中的逻辑都封好，直接体现即代码量少；

可使用jupyter执行方法及时查看语句执行结果；


但是缺少对整个大数据工具处理请求的控制（这个缺点是相对比方法二而言，但是对于该方法面向的用户来说，可以忽略）。

### 方法二： ###

对整个处理流程可控度高；

但是初次写脚本投入的精力和需要理解的内容，以及整理的逻辑相对较多；

该方法需要消耗精力的主要方面如下：

如何利用Python提交rest请求，实现调用GP服务；

如何利用python解析GP服务请求结果。

# 参考： #
1.	ArcGIS 知乎上与ArcGISPythonAPI相关文章链接：http://zhihu.esrichina.com.cn/search/q-UHl0aG9uIEFQSQ==#articles
2.	ArcGIS Python API帮助文档：
https://developers.arcgis.com/python/
3.	从restAPI了解大数据工具：
http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000002sp000000
4.	在Python脚本中调用GP服务
https://enterprise.arcgis.com/en/server/latest/publish-services/linux/using-a-service-in-python-scripts.htm



