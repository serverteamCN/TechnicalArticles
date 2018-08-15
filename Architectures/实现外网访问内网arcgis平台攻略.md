
# 实际需求： #

将物理主机内部的基于docker容器搭建的GA环境对外开放，实现即只要能访问物理宿主机的用户都可以使用该环境执行大数据测试。

相同技术思路也可以作为参考实现：为Portal for ArcGIS 与ArcGIS Server配置反向代理，以实现外网访问内网GA（RA或者GIS Server集群）环境。


# 测试环境： #
物理主机安装了docker 和nginx， 并根据以下帖子在物理宿主机利用docker搭建了GA环境。

http://www.gougexueli.com/2018/07/30/%E5%9C%A8docker%E7%8E%AF%E5%A2%83%E5%86%85%E6%90%AD%E5%BB%BAarcgis%E5%A4%A7%E6%95%B0%E6%8D%AE%E6%B5%8B%E8%AF%95%E7%8E%AF%E5%A2%83/


# 测试网络环境： #
1.	客户端和物理主机在一个网段，可以互相访问；
2.	客户端不能访问物理主机内部的docker容器，即GA环境；

# 储备知识： #
1.	了解arcgis enterprise架构以及server与portal的联合托管关系；
2.	如果是IT人员执行该配置，建议与ArcGIS产品管理员一起协作；

# 前期准备： #

1.	如果在配置nginx前，已经将portal和server联合托管，则需要将两者关系解除，因为此时portal内部记录的URL都是内网地址；
2.	对于在配置反向代理前portal中生成的item资源（来自联合的ArcGIS Server），记录的URL是内网的webadatpor地址，需要将这些item删除，配置好反向代理后再联合，以避免有冗余item。


# 预期结果： #
配置结束后， 你将可以确认以下事情：

1.	外网用户访问和使用是否成功；
2.	server portal 内外网地址列表和整体架构图，方便后续管理；
3.	图一为此次测试环境中生成的架构图，供参考。
	
    可以将图一中的参数擦除，填上自己环境里的真实参数。

    注：datastore作为服务器后面的支持数据库，配置Nginx的时候不需要考虑。




![](https://i.imgur.com/pbsDzvJ.png)




                                          图一

注：此处的webadaptor与arcgis enterprise basic安装在一台机器上，生产环境如果允许，建议单独将webadaptor放置在一台独立的机器上。


# 技术关键点： #

1.	在安装ArcGIS产品的时候，将需要的webadaptor放置在一台机器上，然后nginx将webadaptor所在web server映射出来；
2.	在portal和server内部配置指定其在外网被访问的地址，地址中需要体现各自webadaptor的名字，详见配置步骤；
3.	将portal和server联合托管的时候，在portal中填入外部访问server的地址。



# 操作步骤： #

以下执行默认为各个机器上的软件都已经安装好，且hosting server与GA站点都没有与portal进行联合。






## 1 配置Nginx ##

修改nginx配置文件，即/etc/nginx/sites-enabled/default。

实现：将容器1中的web server 443（即webadaptor所在机器）端口映射到物理宿主机443端口上，配置信息见图二。

![](https://i.imgur.com/o9HUC30.png)
 
                                             图二

注：建议同时调整nginx允许客户端上传的文件大小。


## 2   配置portal ##

对Portal进行设置，指定Portal请求处理后转发出去的URL，确保请求处理完成结果可以返回客户端。

登录portaladmin->System->Properties，然后填入参数WebContextURL，如图三所示。

![](https://i.imgur.com/zgiIFP8.png)
 
                                                图三


配置后获取了portal内网访问地址：

https://gaserver106.esrichina.com:7443/arcgis

https://gaserver106.esrichina.com/arcgis/home(通过webadaptor访问portal站点)

portal外网访问地址：

https://serverpc.esrichina.com/arcgis/home






## 3 配置hosting server ##
	
对hosting server进行设置，指定server请求处理后转发出去的URL，确保请求处理完成结果可以返回客户端。

登录severadmin->System->Properties，然后填入参数WebContextURL，如图四所示。

![](https://i.imgur.com/cCdjBnh.png)
 
                                                图四


配置后获取hosting server内网访问地址：

https://gaserver106.esrichina.com:6443/arcgis/manager

https://gaserver106.esrichina.com/server/manager(通过webadaptor访问hosting server站点)

hosting server外网访问地址：

https://serverpc.esrichina.com/server/manager


注：此时可以测试 -- 在客户端分别访问portal 和server映射出来的地址，并尝试登陆是否成功。


## 4	配置GA站点 ##

对GA 站点进行设置，指定server请求处理后转发出去的URL，确保请求处理完成结果可以返回客户端。

登录severadmin->System->Properties，然后填入参数WebContextURL，如图五所示。

![](https://i.imgur.com/fmHu1us.png)
 
                                                     图五


配置后获取GA 站点内网访问地址：

https://server1061.esrichina.com:6443/arcgis/manager

https://ga1061base.esrichina.com/bigdata/manager(通过webadaptor访问GA站点)

GA 站点外网访问地址：

https://serverpc.esrichina.com/bigdata/manager


## 5   联合托管 ##

将hosting server和GA站点与portal进行联合托管并进行server角色的分配。

注：执行该步骤的时候需要使用步骤2到4中获得的外网访问地址。


## 6    环境测试 ##

映射完毕后，建议在客户端测试以下portal功能：

•	在portal mapviewer 执行大数据分析；

•	在portal mapviewer中通过搜索门户内的图层添加图层；

•	在portal中通过添加本地csv文件，生成托管要素图层。




# 参考文档： #



- 将反向代理服务器与 Portal for ArcGIS 结合使用

http://enterprise.arcgis.com/zh-cn/portal/latest/administer/linux/using-a-reverse-proxy-server-with-portal-for-arcgis.htm



- 将反向代理服务器与 ArcGIS Server 结合使用

http://enterprise.arcgis.com/zh-cn/server/latest/administer/linux/using-a-reverse-proxy-server-with-arcgis-server.htm


# 原文链接： #
http://www.gougexueli.com/2018/08/15/%E5%AE%9E%E7%8E%B0%E5%A4%96%E7%BD%91%E8%AE%BF%E9%97%AE%E5%86%85%E7%BD%91arcgis%E5%B9%B3%E5%8F%B0%E6%94%BB%E7%95%A5/