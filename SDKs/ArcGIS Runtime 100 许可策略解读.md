#ArcGIS Runtime 100 许可策略解读

###概览
ArcGIS Runtime SDK 100 的许可政策，从大方向上依然延续了之前版本的策略。面向开发者支持ArcGIS Runtime SDK的在线下载，并且支持开发模式下的全功能开放。在开发模式下地图或场景依然会打上Esri的水印，在调试消息中会添加仅用于开发使用的声明。SDK的下载和free级别许可的生成需要注册开发者账户，面对中国区开发者账户暂未开放的情况，我们可以通过注册ArcGIS Online试用账户来替代，效果是一样一样的。

在开发结束后，应用要以产品的形式对外发布，这时我们就要关心如何激活Runtime许可，去除水印并获得正版授权。在ArcGIS Runtime SDK 100中，许可级别相较于之前的版本有所调整，Esri提供了四种级别的授权：Lite, Base, Standard和Advanced。

###许可激活模式
针对这四种级别的许可，Esri提供了两种激活许可的方式：license key 和Named User。

* license key是文本字符串，将其添加到Runtime 应用中即可激活许可。这个key对于Lite级别可以通过online账户免费获得，对于更高级别，则需要以ArcGIS Runtime许可包的方式从官方购买。这种方式适合由于网络或安全原因，应用无法连接网络，同时应用本身也不需要访问任何在线服务的场景。

* Named User获取授权，熟悉Esri产品的GISer应该知道Portal for ArcGIS 和ArcGIS Online的授权模式是基于Named User的（ArcGIS组织账户）。为Runtime应用授权是Named User的重要特性之一。授权的过程需要在应用中通过代码登录Online或Portal，然后返回与Named User账户相关的许可信息。使用Named User申请的许可有效期是30天，过期后只需要再次连接Online 或Portal重新申请授权即可。这个许可支持保存到本地用于离线使用，但是牢记30天的有效期，别忘了定期更新许可。这种模式的好处是同一个Named User并不限定授权一个应用，而是可以同时授权很多ArcGIS Runtime apps。

###许可级别对比分析
下面的表格对比了四种许可级别、对应的功能以及两种授权模式之间的对应关系。

|License级别  |功能 |License key|Named user|  
|---|---|---|--|  
|Lite |-浏览地图，场景，图层以及来自ArcGIS的包<br> -简单路网分析 <br> -位置查找|免费可用。在开发者网站生成Licence key，<br>并用其在应用中激活许可|在应用中以Online或Portal的<br>Level1或Level2级别的Named User登陆，并激活许可|  
|Base|-Lite的全部功能<br> -简单要素编辑<br> -portal内容的增，删，改，查<br> -使用ArcGIS Online的分析服务|联系Esri官方，购买部署包|在应用中以Online或Portal的<br>Level2级别的Named User登陆，并激活许可|  
|Standard|-Basic的全部功能<br> -访问本地栅格及本地栅格高程数据源<br>-ArcGIS Runtime Local Server 标准版功能|联系Esri官方，购买部署包|暂不可用|  
|Advanced|-Standard的全部功能<br> -ArcGIS Runtime Local Server高级版功能|联系Esri官方，购买部署包|暂不可用|  

####_注意_：
* 从ArcGIS 10.5开始，ArcGIS Online或者Portal for ArcGIS的成员有两种许可级别供选择。Level1 可以被用来授权Runtime Lite级别的许可，Level2可以被用来授权Lite和Basic级别的许可。对于10.5之前的portal，所有的Named User等效于Level2,可以被用于激活Runime Lite和Basic级别的许可。
* ArcGIS Runtime Local Server仅可以用于面向桌面的ArcGIS Runtime SDKs: Runtime SDK for .NET(WPF), Runtime SDK for Java,Runtime SDK for Qt。

###扩展
ArcGIS Runtime提供了下列可选扩展，以支持其它的功能，分析工具和数据：

ArcGIS Runtime Local Server 的 GP Services

- Analysis
- Network Analyst
- Spatial Analyst
- 3D Analyst

###激活许可向导
在完成应用开发和测试后，可以通过以下向导完成许可的激活，以消除底图水印并获得正版官方授权。

####License key模式激活许可
#####通过ArcGIS Online申请免费许可
1、注册ArcGIS Online试用账号或者Esri开发者账号（中国区暂不支持）
打开浏览器，访问www.arcgis.com网站，点击Try ArcGIS按钮，按照页面向导，注册用户。
插入图片1

2，访问ArcGIS Runtime/Licensing页面，以前一步注册的试用账户登录网站
打开浏览器，访问https://developers.arcgis.com/arcgis-runtime/licensing/，点击右上角的Sign In登录。  
登录成功后，点击Show my ArcGIS Runtime Lite license key按钮，即可获得免费的Lite级别的许可。
插入图片2
许可格式规则：
runtimelite,1000,rud****,none***********

#####购买runtime SDK授权包
如果是从官方购买ArcGIS Runtime SDK的授权包，将会获得来自官方的授权文件，可以取文件中的授权码直接使用。

#####License key激活许可示范
For .NET, Java, Android:

```
// license with a license key
ArcGISRuntimeEnvironment.setLicense("runtimelite,1000,rud#########,day-month-year,####################");
```

For iOS:

```
//license the app with the supplied License key
do {
 let result = try AGSArcGISRuntimeEnvironment.setLicenseKey("runtimelite,1000,rud#########,day-month-year,####################")
 print("License Result : \(result.licenseStatus)")
}
catch let error as NSError {
 print("error: \(error)")
}
```

####Name User模式激活许可
前面已经讲过，通过Online 或者Portal的Named User也可以授权Runtime 应用,整个过程需要编程实现。详细的授权过程，可以参照以下链接中的示范工程来激活许可：

- [For .NET]()
- [For Java]()
- [For Andoid]()
- [For iOS]()





