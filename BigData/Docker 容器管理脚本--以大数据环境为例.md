# 目的： #
	在docker中通过执行脚本管理大数据环境容器以及容器内部的服务，快速启动一套测试环境。
	在文章《在Docker环境内搭建大数据测试环境》中我们讨论了如何在docker环境内搭建矢量大数据测试环境,
	按照以下保守思路搭建，我们需要5台容器：ArcGIS Enterprise基础部署一个容器，GA一个容器，时空库三台容器。
	如果按照上述文章搭建完成后，我们面临管理多个容器的现实问题。
	这篇文章要实现的是：容器停止后，如何实现自动化启动容器以及容器内部的服务（ArcGIS Portal， Server和Datastore），
	从而提高工作效率。



# 效率：  #


	一键执行脚本，代替反复动手敲入命令，每次管理任务保守估计节约成本1小时。

# 实现： #
	想要实现目的，我们需要实现两个问题：

	Q1.如何生成Linux shell脚本文件
	该问题是通用问题，可以在网上找到解决答案，此处不再赘述。

	Q2.shell脚本中的内容，即如何实现管理

	针对每台容器都需要执行以下两步：
		首先，开启容器；
		其次，进入到容器内部，开启ArcGIS 相关服务。


	以下以开启portal所在容器和其服务为例。
	
	*启动portal所在容器，容器名字为beportal*
	docker start beportal

	*按照预先分好的hosts映射表分配IP*
	pipework docker0 -i eth0 beportal 172.17.0.20/24@172.17.0.1

	*拷贝hosts文件到docker内部*
	docker cp /etc/hosts beportal:/home/

	*在docker内部执行命令*
	docker exec -i beportal bash << EOF

	*将hosts文件拷贝到最终的文件目的地*
	/bin/cp -rf /home/hosts /etc/hosts
	
	*进入到portal的安装目录*
	cd /home/arcgis/arcgis/portal

	*切换到arcgis即portal安装用户*
	su arcgis

	*执行启动portal服务脚本*
	./startportal.sh
	EOF

	*在脚本执行框将完成状态告知用户*
	echo 'beportal started'



	利用上述思想，完成对GA 容器和服务，以及时空库（ArcGIS Datastore）容器的和服务管理的改写，
	根据需求，将所有内容放在一个脚本中，或者分开放都可。
	Enjoy your script！
