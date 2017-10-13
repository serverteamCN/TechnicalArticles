"""
The root of all OAuth2 resources and operations.
"""
import os
import json
########################################################################
class OAuth(object):
    """
    The root of all OAuth2 resources and operations.
    """
    _gis = None
    _con = None
    _portal = None
    _url = None
    #----------------------------------------------------------------------
    def __init__(self, url, gis):
        """Constructor"""
        self._url = url
        self._gis = gis
        if self._gis is not None:
            self._con = gis._con
        self._portal = gis._portal
    #----------------------------------------------------------------------
    def authorize(self,
                  client_id,
                  response_type,
                  redirect_uris,
                  client_secret=None,
                  state=None,
                  expiration=None,
                  display=None,
                  locale=None,
                  persist=True,
                  ssl=True):
        """
        The Authentication topic describes the overall OAuth2 authentication
        flow. This topic describes the user authorization step of that
        flow.
        Apps that support user logins use OAuth2 to allow users to log in
        to the ArcGIS platform via the app.
        User logins using the OAuth2-based ArcGIS APIs are based on the
        application guiding the user to log in to the platform via a login
        page hosted on the ArcGIS platform. The /oauth2/authorize endpoint
        represents that login page. The login page renders an HTML form for
        the user to enter their credentials.
        The user authentication workflow starts with the authorization
        step. Apps need to direct the browser to this URL. client_id,
        response_type, and redirect_uri are required parameters. There are
        other optional parameters as well, and they;'re described below.
        The response_type parameter determines the type of grant - implicit
        or authorization. A response_type of token implies implicit grant
        and code implies authorization code grant.
        Implicit grants are typically used by JavaScript applications, and
        they complete the flow in a single step. The end result of
        successful authentication is an access_token that's delivered to
        the specified redirect_uri in the URL fragment. See the Response
        section for details.
        Authorization grants are used by mobile, desktop, and server-side
        applications, and they complete the flow in two steps.
        Authorization represents the first step of that flow. Successful
        authorization yields an authorization code that's delivered to the
        specified redirect_uri as a query parameter. See the Response
        section for details. The second step of the flow requires
        exchanging the authorization code obtained in the first step for an
        access_token. This is accomplished by accessing the token endpoint
        with a grant_type of authorization_code.

        Parameters:
         :client_id: The ID of the registered application. Also referred to
          as APPID.
         :response_type: The type of grant - implicit or authorization.
          Values: token, code
          token implies implicit grant and code implies authorization code
          grant.
         :redirect_uris:The URI where the access_token or authorization
          code will be delivered upon successful authorization. The URI
          must match one of the URIs specified during app registration,
          otherwise authorization will be rejected. If registered, a
          special value of urn:ietf:wg:oauth:2.0:oob can also be specified
          for authorization grants. This will result in the authorization
          code being delivered to a portal URL (/oauth2/approval). This
          value is typically used by applications that don't have a web
          server or a custom URI scheme where the code can be delivered.
         :client_secret: The secret of the registered application. Also
          referred to as APPSECRET.
         :state: An opaque value used by applications to maintain state
          between authorization requests and responses. The state, if
          specified, will be delivered back to the redirect_uri as is.
          Applications can use this parameter to correlate the
          authorization request sent with the received response.
         :expiration: The requested validity in minutes of access_token for
          implicit grants or refresh_token for authorization grants.
          For implicit grants, the default validity of access_tokens is 2
          hours. The expiration parameter, if specified, overrides the
          validity period up to a max of 2 weeks (i.e., 20160 minutes).
          For authorization grants, the default validity of access_tokens
          is 30 minutes and refresh_tokens is 2 weeks. The expiration
          parameter, if specified, overrides the validity period of
          refresh_tokens. A permanent refresh_token can be requested by
          specifying expiration=-1.
          Note that org admins can specify the max validity period of
          tokens for their org that supercedes the expiration parameter.
         :display: The template used to render the login page.
          Based on the client platform, applications can choose one of the
          supported templates to render the login page. If not specified,
          the default template is used.
          Values: default, iframe, win8
         :locale: The locale assumed to render the login page.
          Applications can pass the user's locale using this parameter. The
          login page will be rendered using the language corresponding to
          that locale. If not specified, the locale will be determined
          based on the org's setting or on the incoming request.
          Example: locale=fr
         :persist: If true, implies that the user had checked "Keep me
          signed in" when signing into ArcGIS Online.
         :ssl: If true, implies that the user belongs to an ssl-only
          organization
        """
        url = "%s/authorize" % self._url
        params = {
            "f" : "json",
            "redirect_uri" : redirect_uris,
            "response_type" : response_type,
            "client_id" : client_id
        }
        if ssl:
            params['ssl'] = ssl
        if persist:
            params['persist'] = persist
        if locale:
            params['locale'] = locale
        if display:
            params['display'] = display
        if expiration:
            params['expiration'] = expiration
        if state:
            params['state'] = state
        if client_secret:
            params['client_secret'] = client_secret
        return self._con.post(path=url,
                              postdata=params)
    #----------------------------------------------------------------------
    def apps(self, client_id):
        """
        An app registered with the portal. An app item can be registered by
        invoking the register app operation. Every registered app gets an
        App ID and App Secret which in OAuth speak are known as client_id
        and client_secret respectively.
        The app owner has access to the registered app resource. This would
        include the organization administrator as well.

        Parameters:
         :client_id: The ID of the registered application. Also referred to
          as APPID.
        """
        url = "%s/apps/%s" % (self._url, client_id)
        params = {"f" : "json"}
        return self._con.post(path=url, postdata=params)
    #----------------------------------------------------------------------
    def register_device(self, client_id, expiration=None):
        """
        Registers a device, like mobile phone with a client id to access a
        given portal/AGOL.

        Parameters:
         :client_id:The ID of the registered application. Also referred to
          as APPID.
         :expiration: The requested validity in minutes of access_token for
          implicit grants or refresh_token for authorization grants.
          For implicit grants, the default validity of access_tokens is 2
          hours. The expiration parameter, if specified, overrides the
          validity period up to a max of 2 weeks (i.e., 20160 minutes).
          For authorization grants, the default validity of access_tokens
          is 30 minutes and refresh_tokens is 2 weeks. The expiration
          parameter, if specified, overrides the validity period of
          refresh_tokens. A permanent refresh_token can be requested by
          specifying expiration=-1.
          Note that org admins can specify the max validity period of
          tokens for their org that supercedes the expiration parameter.
        """
        url = "%s/registerDevice" % self._url
        params = {
            "f" : "json",
            "client_id" : client_id
        }
        if expiration:
            params['expiration'] = expiration
        return self._con.post(path=url,
                              postdata=params)
    #----------------------------------------------------------------------
    def token(self,
              client_id,
              grant_type,
              redirect_uri,
              code=None,
              refresh_token=None,
              client_secret=None):
        """
        TODO: Update Docs
        """
        params = {
            "f" : "json",
            "client_id" : client_id,
            "grant_type" : grant_type
        }

    #----------------------------------------------------------------------
    def register_app(self,
                     item,
                     redirect_uris,
                     app_type="browser"):
        """
        The register app operation (POST only) registers an app item with
        the portal. App registration results in an APPID and APPSECRET
        (also known as client_id and client_secret in OAuth speak,
        respectively) being generated for that app. Upon successful
        registration, a Registered App type keyword gets appended to the
        app item.
        Available to the item owner.

        Parameters:
         :item: arcgis.gis.Item object
         :redirect_uris:The URIs where the access_token or authorization
          code will be delivered upon successful authorization. The
          redirect_uri specified during authorization must match one of the
          registered URIs, otherwise authorization will be rejected.
          A special value of urn:ietf:wg:oauth:2.0:oob can also be
          specified for authorization grants. This will result in the
          authorization code being delivered to a portal URL
          (/oauth2/approval). This value is typically used by apps that
          don't have a web server or a custom URI scheme where the code can
          be delivered.
         :app_type:The type of app that was registered indicating whether
          it's a browser app, native app, server app, or a multiple
          interface app.
          Values: browser | native | server| multiple
        """
        url = "%s/registerApp" % self._url
        itemid = item.id
        params = {
            "f" : "json",
            "itemid" : itemid,
            "appType" : app_type,
            "redirect_uris" : redirect_uris
        }
        return self._con.post(path=url,
                              postdata=params)


