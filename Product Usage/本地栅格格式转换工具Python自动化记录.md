# 目的： #

实现利用Python脚本执行本地栅格格式的转换，可利用的工具包含两个：

1.CopyRaster--Esri提供的GP工具；

2.gdal_translate-- GDAL提供的栅格格式转换工具；

两个工具支持的栅格格式不同，需要时，可以将gdal_translate作为CopyRaster工具的补充。

# 本文主要包含以下两个内容： #

1.调用两个工具所需要的前期环境搭建准备；

2.调用两个工具的Python示例脚本。

# 具体实现： #

## 1.	如何实现调用CopyRaster—环境准备: ##
	
1.1 Windows系统中如果安装了ArcMap或者ArcGIS Pro, 其随之安装的Python环境都包含arcpy，可以直接调用arcpy。

1.2 Linux系统上安装了ArcGIS Server 10.5及以上版本后，可以通过独立安装Python3 runtime，搭建环境，调用arcpy。

参考链接：https://github.com/serverteamCN/TechnicalArticles/blob/master/Product%20Usage/%E5%9C%A8Linux%E4%B8%AD%E6%90%AD%E5%BB%BAPython3runtime%E6%80%BB%E7%BB%93%E6%89%8B%E5%86%8C.md


## 2.	如何实现调用CopyRaster—示例代码： ##

请直接参考Esri官方帮助：
http://pro.arcgis.com/en/pro-app/tool-reference/data-management/copy-raster.htm


## 3.	如何实现调用gdal_translate—环境准备： ##

3.1 Windows系统中，如果安装了ArcGIS Pro 1.3及以上版本,可以直接利用随之安装的conda下载GDAL包，如下图：
![](https://i.imgur.com/xX50peu.png)

 
如果没有安装ArcGIS Pro1.3及以上版本，独立安装gdal参考帮助文档：
https://viewer.nationalmap.gov/tools/rasterconversion/gdal-installation-and-setup-guide.html

3.2 Linux系统中，未尝试使用；但是理论上可以将windows中实现的思想移植到Linux上，即下载Anaconda，然后通过conda安装gdal。


## 4.	如何实现调用gdal_translate—示例代码： ##
参考附件1-gdal_translate.py


# 附件及参考： #
1. 	Python脚本实现利用gdal_translate转换栅格格式
	https://github.com/AlisonGou/demo/blob/master/gdal_translate.py

1. CopyRaster支持的格式参考：
	http://pro.arcgis.com/en/pro-app/tool-reference/data-management/copy-raster.htm 

1.  gdal_translate帮助： 
	 http://www.gdal.org/gdal_translate.html

1.  gdal栅格支持格式帮助：
	 http://www.gdal.org/formats_list.html

1.  gdal帮助：
	http://www.gdal.org/
