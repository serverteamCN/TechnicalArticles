# 通过python自动化修正矢量切片符号和标注压盖问题 #


通过Pro2.0生成矢量切片时，我们会发现针对点图层，生成的矢量切片在绘制时会出现标注略微压盖符号的现象。  

![标注压盖符号样图](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题01.png)

## 1 问题分析  

这个问题可以说是现行版本中矢量切片拾取Pro制图参数之间存在一定的技术缺陷引起的，毕竟矢量切片技术遵从的是Mapbox style 规范来绘制地图和Pro中的制图规则并不完全一致，官方预计在未来版本中会针对这个问题增强修复。

## 2 规避方案   

矢量切片最大的优势之一就是可以基于现有切片自定义符号。当然，一般的自定义符号我们是根据现有的配置参数更改值，来实现地图样式的再定制。那是否可以通过增加参数来解决标注和符号的压盖问题呢？答案是肯定的，在Mapbox规范中包含了"text-offset"参数，可以用来实现标注的偏移：
![text_offset参数](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题02.png)

＊说明：“Ems”单位是被用于网页文件媒介的可缩放的单位（即相对单位）。1em就等于当前字体的大小，举个例子来讲，如果文档中字体的大小为10pt，那么1em = 10pt。

接下来我们就动手修复这个问题吧！

### 修复过程：  


1）通过Pro生成矢量切片包，具体的生成过程参照官方帮助：[创建矢量切片包](http://pro.arcgis.com/en/pro-app/tool-reference/data-management/create-vector-tile-package.htm);

2）将vptk包拷贝到测试目录，并修改扩展名为zip；

3）解压缩，获取矢量切片样式文件root.json所在目录，默认目录结构参考：<解压缩后目录>\p12\resources\styles\root.json  

4）用记事本或浏览器打开这个文件，我们可以看到每一个图层的样式和标注分类已经被重新调整为新的layer。如果图层数很少，那找到我们要修改的图层id，手动对其添加“text-offset”参数就可以了。但是如果图层数量过多，手动修改每个图层参数显然不现实，一来容易出错，二来工作量也太大，并且不够灵活。这时，我们就可以通过python编程解析并修改root.json文件。为了方便大家，我写了一个精简版的自动化脚本工具可以通过以下地址获取：[自动化修改矢量切片样式工具](https://github.com/makeling/VTPKPythonTools/blob/master/repairtextoffsettool.py) 

自动化脚本工具执行过程：  
![执行过程](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题06.png)   

在控制台中执行自动化修改工具会返回：  
－ 当前切片包中的图层总数；  
－ 返回当前切片包的图层列表；   
－ 根据图层列表返回的值，在控制台中交互输入要修改的图层名（如果要修改多个图层可以简写名称匹配多个图层）；  
－ 执行修改操作，并返回修改的图层列表； 

检验root.json文件：  
修改前：  
![text_offset参数修改前](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题03.png) 

修改后：  

![text_offset参数修改后](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题04.png)

5）修改完成后，将之前解包后的esriinfo,p12文件夹重新压缩为zip包（注意压缩文件夹结构不要含父级目录，压缩类型选择存储格式）；  

6）再次修改包扩展名为vtpk。  

至此，我们的修复工作就完成了，接下来就是鉴证奇迹的时刻...

## 3 发布vtpk包，检验成果  
 

检测过程包括两个关键环节：  

1）检测修改后的vtpk有效。这个判断准则就是在上传vtpk包时，我们勾选的同步发布一个Vector Tile Service是否可以成功发布。如果矢量切片服务可以成功发布出来，就说明包的修改已经成功了。如果不能发布，要检测修改后再压缩的zip包是否多打了一级目录，这样的压缩包是不会被portal正确识别的。  

2）验证标注已经正确偏移。下图是我修改后的结果：
![成果验证](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/通过python自动化修正矢量切片符号和标注压盖问题05.png)





