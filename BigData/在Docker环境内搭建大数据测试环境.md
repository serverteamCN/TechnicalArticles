**目标**：实现在已有的docker环境中安装产品，搭建一套矢量大数据的测试环境。


**前提**：已经有docker环境，明白镜像和容器的概念；并且熟悉在Linux环境下安装ArcGIS Server。


Linux 上安装 ArcGIS Enterprise 超详细教程参考
https://github.com/serverteamCN/TechnicalArticles/blob/master/Product%20Usage/Linux%20%E4%B8%8A%E5%AE%89%E8%A3%85%20ArcGIS%20Enterprise%20%E8%B6%85%E8%AF%A6%E7%BB%86%E6%95%99%E7%A8%8B%E2%80%94%E2%80%94%E4%BB%A5%20Redhat%207.2%20%E4%B8%8A%E5%AE%89%E8%A3%85%20ArcGIS%20Enterprise%2010.5%20%E4%B8%BA%E4%BE%8B.md


Linux上ArcGIS 10.5 GeoAnalytics集群环境部署指南参考
https://github.com/serverteamCN/TechnicalArticles/blob/master/BigData/Linux%E4%B8%8AArcGIS%2010.5%20GeoAnalytics%E9%9B%86%E7%BE%A4%E7%8E%AF%E5%A2%83%E9%83%A8%E7%BD%B2%E6%8C%87%E5%8D%97.md


**为什么用docker？**


- 可以充分利用短缺的计算机资源；

- 方便管理：直接用命令行或者写脚本启动容器，甚至是容器里面的ArcGIS Server服务。


**测试环境机器资源配置：**

- 物理机主机CPU：16核

- 物理机主机内存：76GB


**当前测试环境中大数据架构包含：**

- 一套基础ArcGIS Enterprise部署；

- 一台GA服务器；

- 三台时空数据库。


# **想要实现目标主要包含以下三个方面的实现：** #

1. 前期设计；

1. 创建镜像；

1. 启动容器。



# **具体执行步骤** #


## **前期设计：** ##

**前期设计需要考虑以下两点：**

1.	设计GA环境中每台机器的全域名和IP，需要将这张表映射到每台机器（每个容器）hosts文件中，确保各个容器之间可以正常通信；webadaptor可以不单独放置在某台机器上，但是需要注意在ArcGIS Enterprise中portal和server需要使用各自的webadaptor。
![](https://i.imgur.com/F4VjW0F.png)

                                       表一 Docker环境下大数据机器映射表



2.	设计镜像，需要预先想好每个镜像里包含的内容，主要为了后期快速生成容器。
![](https://i.imgur.com/NWrgA8y.png)

                                         表二 镜像




## **创建镜像：** ##
以下以创建镜像agsserver1051base为例，记录整个执行过程。

物理机docker中已经有一个基础镜像，名字为merry/cent_ags105_baseos，其中已经包含了tomcat和jdk，以这个镜像为基础去生成新的镜像。





1. 将ArcGIS Server安装包上传到容器中，为了避免每次都传输安装介质，在volume上创建共享文件夹 命名为arcgis_installation_media，然后将ArcGIS安装包放在这个目录下，创建语句如下：


     docker volume create arcgis_installation_media



     在物理主机以下位置会出现新创建的文件夹：

     ![](https://i.imgur.com/CSzqboc.png)
 






2. 根据基础镜像创建容器，安装ArcGIS Server。创建容器的命令如下：

     docker run -it --mount source=arcgis_installation_media,target=/home/installation_files merryesri/cent_ags105_baseos

     上述命令将arcgis_installation_media挂载到新创建的容器中，避免重复拷贝安装介质到新容器中。安装ArcGIS Server，但不创建站点，此处不再赘述安装ArcGIS Server。


3. 将上一步的容器打包成搭建GA环境的基础镜像，命令如下：

    docker commit agsserver1051base merryesri/cent_ags105_baseos


5.	重复执行上述1到3步，实现全部基础镜像的生成工作。



如果全部基础镜像都已经生成，在启动容器前，还需要做以下准备：

1.	在volumes下面生成文件夹，作为GA站点集群的共享存储。此处生成的文件夹为MA_gaserversite；

2.	可以先根据设计的大数据机器映射表将所需要的IP与主机名在hosts文件中做映射，然后将该hosts文件拷贝到volume下的MA_gaserversite下。




## 启动容器：  




1. 执行以下命令启动容器作为GA Server


    docker run -itd --mount source=MA_gaserversite,target=/home/arcgisserver --name  gaserver1 --net none --hostname ganode1.esrichina.com -v /etc/localtime:/etc/localtime agsserver1051base


    其中--mount source=MA_gaserversite,target=/home/arcgisserver意思是在创建容器的时候会生成一个arcgisserver文件夹，并将主机的MA_gaserversite文件夹挂载给它。


     -v /etc/localtime:/etc/localtime可以确保容器和主机的时间一致。


     --net none 生成容器的时候不指定网络。


     --hostname ganode1.esrichina.com 指定新容器的全域名

 

1. 执行以下语句指定新起容器的IP：

    pipework docker0 -i eth0 gaserver1 172.17.0.21/24@172.17.0.1




1. 进入到新创建的容器内：
    
    docker attach gaserver1
    
    将arcgisserver下的hosts文件拷贝到/etc/下。



1. 启动ArcGIS Server服务，然后创建站点。




1. 临时退出该容器，继续启动其他容器，使用如下语句退出但是保持容器运行：Control-P Control-Q。


按照上述步骤完成所有的容器创建和站点创建后，即可执行Portal for ArcGIS 与ArcGIS for Server的关联，完成搭建GA环境。
