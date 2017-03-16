# ArcGIS Runtime SDK 100.0.0 Loadable设计模式剖析

在基于ArcGIS SDK开发的各平台地图应用中，都会涉及到很多资源型对象，比如基于远程服务的layers, maps, portal items和tasks，基于离线地图的offline geodatabase, Mobile map package等对象。

参照帮助文档中的样例，可能很多ArcGIS开发者都知道如何初始化一个Map, 如何在Map中添加Layer，如何将一个portal中的Item添加到地图中，但是可能很多人都不会意识到在使用资源型对象时，这些对象的初始化过程实际上封装了对远程在线服务或本地资源的异步请求，获取资源的元数据过程。而只有成功返回元数据结果的资源对象，才算初始化成功，我们才能进一步获取像LayerInfo，MapServiceInfo，地图初始范围等等资源属性信息。

那么如何判断资源的初始化过程进行到哪一步了？是否对象已经成功初始化？在之前版本的SDK中资源对象的初始化过程都是封装在各个对象中的，并不存在统一的方法或者说统一的架构，监控初始化状态更是无从谈起。在100.0.0版本中针对资源型对象的加载模式，Esri重新进行了设计，所有资源型对象实现统一的加载方法，请求状态可监控，请求过程可干预，同时解决了同一实例对象在多次使用时，重复初始化的问题，进一步优化了异步请求加载流程。

这篇文章我以ArcGIS Runtime SDK for iOS 100.0.0版本为例，为大家详细的剖析Loadable设计模式的思想以及能实现的功能。


>约定： 在100.0.0中所有采纳loabable设计模式的资源，我们都称为是可加载的（loadable）资源。在IOS中判断是否为“Loadable”资源的方法，就是判断该类是否采纳了“\<AGSLoadable>”协议。

### 1. Loadable设计模式的核心功能    
  
Loadable设计模式是在SDK中维护的一套针对可加载资源的自适应初始化逻辑，核心能力包括以下几方面：

－资源加载逻辑统一维护，加载一次，处处使用，避免重复请求加载；  
－允许针对之前加载失败的资源重新尝试加载；  
－加载过程中，允许取消；  
－提供统一的加载状态编码，便于细粒度监控加载过程。  

### 2. 资源加载流程分析   
  
对于所有可加载的资源，当我们对其初始化时，这个对象会经历以下资源加载过程：
![资源加载状态流程](https://raw.githubusercontent.com/serverteamCN/TechnicalArticles/master/pictures/Loadable设计模式剖析01.png)
  
    
对于所有的可加载资源:  

－ 当触发`loadWithCompletion：`方法时，就开启了异步元数据加载流程。这时，请求状态从`Not Loaded` 切换为`Loading`;

－ 在异步操作完成时，回调（completion block）方法会被触发：  
&emsp;&emsp;  ＊ 如果请求返回错误，回调错误参数会被赋值，加载状态会被设置为`FailedToLoad`;  
&emsp;&emsp; ＊ 如果请求执行成功，错误参数为null，加载状态变为`Loaded`状态。

### 3. 多请求合一原理  
  
很多情况下，同一个资源实例会在应用的不同部分共享，例如同一个layer，可能既会用于地图，也会用于返回图例信息，还可能用于查询。同一个portal实例，可能既会用于显示用户的项目和也会用于返回群组信息。为了满足这类需求，Loadable设计模式支持多“listeners”,也可以叫并发或者重复，具体的执行逻辑是：当我们在程序中多次触发`loadWithCompletion:`方法，也就相当于多次触发初始化操作，同时添加多次回调监听：    
  
&emsp;&emsp; －如果当前状态码为`Loading`状态，其它请求会被简单的合并，只有一个请求发送到服务端，在操作完成时，回调方法会依次排队触发。  
&emsp;&emsp; －如果当前状态码为`Loaded`或`Failed To Load`状态,回调方法会直接触发，使用过去的结果，状态维持不变。

基于这个逻辑，我们在程序中就可以自由的触发`loadWithCompletion: `请求，不用提前检测资源是否已经加载，也不用担心每次造成不必要的重复网络请求负载，给开发逻辑编写带来了灵活性。  
   
到这儿，细心的读者一定会发现这个逻辑，哪儿隐隐存在问题，如果请求一旦触发，结果维持不变，那成功还好，如果失败了，岂不是会影响后续所有的回调结果？如果之前请求结果失败是由于网络故障，或者服务器偶发性中断，那该如何重新发起初始化逻辑，而不用创建新的实例对象？这个问题Esri是考虑到的，解决办法就是允许重新加载处理失败的请求。
  
### 4.重新加载处理失败请求

遵从多请求合一的逻辑，针对之前失败的请求，如果希望重新尝试加载，那需要使用`retryLoadWithCompletion: `方法，而不是再次调用`loadWithCompletion:`方法，因为这个方法会直接回调返回`Failed To Load`结果。在调用`retryLoadWithCompletion: `方法时，有一点是需要注意的，只有实例对象之前的状态是`FailedToLoad`或`NotLoaded`时，重新加载元数据的请求才会执行，请求状态会切换为`Loading`，执行成功后，返回回调方法，状态更新为`Loaded`。
  
### 5. 取消加载  

对于正在加载中（Loading）的对象，可能因为各种原因出现阻塞，为了不影响整个应用的性能，可以通过触发`CancelLoad:`方法来取消加载。取消后，状态会从`Loading` 切换为`FailedToLoad`。这个方法应该小心使用，因为一旦取消，针对该资源实例的所有回调队列都将取消。如果资源状态不是`Loading`，那么触发`cancelLoad:`方法，将不会执行任何操作。  
  
### 6. 层叠加载依赖  

在地图应用中涉及的很多可加载资源都存在资源依赖的情况，比如，一个portal item 在父portal对象完成加载前，不会完成加载。 Feature Layer需要依赖Feature Table的成功加载。加载操作可以基于任何可加载资源触发，依赖的资源初始化加载过程会顺次触发。在这里需要注意资源对象之间的依赖有两种类型，官方对此没有明确命名，为了讲解方便，我将其暂称为`强依赖`和`弱依赖`。  

&emsp;&emsp; －强依赖，代表依赖资源实例如果创建失败，那么触发请求的资源实例初始化即失败。这一类的对象比如：AGSFeatureTable和AGSFeatureLayer, AGSPortalItem和 AGSPortal。
  
&emsp;&emsp; －弱依赖，代表依赖资源实例之间是松耦合关系，依赖资源实例初始化失败，并不会触发请求资源实例初始化失败。比如AGSMap & AGSLayer等，一个Map中可能包含很多图层，任意图层的初始化失败，并不会触发AGSMap对象的初始化失败，它们是弱依赖关系。这也就意味着，如果地图中某个图层，因为各种原因无法访问了，你的应用是可以正常运行的，其它的地图依然可以正常显示。
  
&emsp;&emsp; 在处理有层叠依赖关系的资源实例时，我们并不需要每个资源都依次触发`loadWithCompletion:`方法，这个初始化链儿会自动执行，所有存在依赖关系的资源实例都会被自动触发初始化，最终的结果会回调到触发初始化的资源实例回调方法中。如果在执行过程中，任意一级强依赖关系的资源实例初始化失败，错误会冒泡反回到最初触发加载循环的实例。  
  
下面我们来看一段层叠加载的示例：  

```
//assign map to the map view
self.mapView.map = map
        
//initialize service feature table using url
self.featureTable = AGSServiceFeatureTable(URL: NSURL(string: "https://sampleserver6.arcgisonline.com/arcgis/rest/services/Energy/Geology/FeatureServer/9")!)
        
//create a feature layer
 self.featureLayer = AGSFeatureLayer(featureTable: featureTable)
        
//add the feature layer to the operational layers
self.map.operationalLayers.addObject(featureLayer) 
```
  
这是非常常见的一段代码，map, featureTable, featureLayer这些对象之间都存在着依赖关系，我们并没有调用`loadWithCompletion:`方法触发初始化，但是在将map赋值给mapView时，所有的依赖对象都将顺次的被初始化。我通过一段监控状态代码返回整个依赖链状态码的变化：  
  
```  
//监控返回加载状态结果：
Map Load status : Loaded
Feature Table Load status : Loading
Feature Layer Load status : Loading
Feature Table Load status : Loaded
Feature Layer Load status : Loaded
```
从这个监控结果能看出来Map首先完成加载，虽然Layer添加到Map,会赋值Map的属性，但是它们是弱依赖关系，回调结果会首先返回，状态码为`Loaded`，后续的加载过程FeatureLayer需要依赖FeatureTable的成功加载才能完成初始化，他们是强依赖关系。



### 7.重写初始化状态

可加载资源在完成加载前，不会被适当的初始化。如果这时访问该资源实例的属性，可能返回null，或者在资源完成加载时，未初始化值可能改变。因此，建议对于可加载资源对象，一定要等待资源完成加载再访问它的属性。然而，很多时候，特别是在原型阶段，在资源加载前可能想预设某些属性值，而不管它的实际属性值是什么。例如，我们可能想改变图层的可见比例尺或者地图的初始viewpoint。为了简化工作流，而不是必须首先加载资源，可加载资源允许在完成加载前重载属性值，并且`重写值将优先于资源元数据指定的值` 这是非常有用，且重要的特性。下面这段代码，可以帮助开发者理解重载的优先级含义。    
  
```
self.layer = AGSArcGISMapImageLayer(URL: NSURL(string: "https://sampleserver6.arcgisonline.com/arcgis/rest/services/Census/MapServer")!)
self.layer.minScale = 5000
self.layer.maxScale = 100000

self.layer.loadWithCompletion { (error) -> Void in
  // layer初始化请求结果，将返回这个回调block，重载的最小，最大比例尺仍将保留，资源加载完成时，来自服务图层的最大、最小比例尺属性值并不会替代这两个预设值。
}
```

### 8.监控加载状态  
  
通过前面的介绍，我们基本了解了Loadable设计模式中涉及的四种加载状态：  
－Not Loaded : 加载元数据的请求还没有被提交的状态  
—Loading : 资源正在执行异步请求加载元数据的状态  
—Failed To Load: 资源初始化获取元数据失败状态（例如，由于网络原因，或者操作被取消等等）  
－Loaded ： 资源加载元数据成功状态
  
 下面这段代码演示下在iOS应用中，监控资源对象加载状态的的过程。
  
  
```
//add Observer for load Status
self.map.addObserver(self, forKeyPath: "loadStatus", options: .new, context: nil)
－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－

func observeValueForKeyPath(keyPath: String?, ofObject object: AnyObject?, change: [String : AnyObject]?, context: UnsafeMutableRawPointer) {
       
     //get the string for load status
     let maploadStatusString = self.loadStatusString(status: self.map.loadStatus)
        
      //set it on the banner label
      print("Map Load status : \(maploadStatusString)")
        
－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－
  
private func loadStatusString(status: AGSLoadStatus) -> String {
        switch status {
        case .failedToLoad:
            return "Failed_To_Load"
        case .loaded:
            return "Loaded"
        case .loading:
            return "Loading"
        case .notLoaded:
            return "Not_Loaded"
        default:
            return "Unknown"
        }
    }
    
```

