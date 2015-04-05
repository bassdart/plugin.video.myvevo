# -*- coding: utf-8 -*-
# VEVO Addon

import sys
import httplib
import urllib, urllib2, cookielib, datetime, time, re, os, string
import xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, xbmc
import cgi, gzip
from StringIO import StringIO
import json



VEVOBASE = 'http://www.vevo.com%s'
VEVOAPI  = 'https://apiv2.vevo.com%s'
UTF8     = 'utf-8'

addon         = xbmcaddon.Addon('plugin.video.myvevo')
__addonname__ = addon.getAddonInfo('name')
__language__  = addon.getLocalizedString

qp  = urllib.quote_plus
uqp = urllib.unquote_plus

home          = addon.getAddonInfo('path').decode(UTF8)
icon          = xbmc.translatePath(os.path.join(home, 'icon.png'))
addonfanart   = xbmc.translatePath(os.path.join(home, 'fanart.jpg'))
maxitems      = 25

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def demunge(munge):
        try:    munge = urllib.unquote_plus(munge).decode(UTF8)
        except: pass
        return munge

USER_AGENT    = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36'
defaultHeaders = {'User-Agent':USER_AGENT, 
                 'Accept':"text/html,application/xhtml+xml,application/xml,application/json;q=0.9,image/webp,*/*;q=0.8", 
                 'Accept-Encoding':'gzip,deflate,sdch',
                 'Accept-Language':'en-US,en;q=0.8'} 

def getRequest(url, user_data=None, headers = defaultHeaders , alert=True, doPut=False, doDelete=False ):

              log("getRequest URL:"+str(url))
              if addon.getSetting('us_proxy_enable') == 'true':
                  us_proxy = 'http://%s:%s' % (addon.getSetting('us_proxy'), addon.getSetting('us_proxy_port'))
                  proxy_handler = urllib2.ProxyHandler({'http':us_proxy})
                  if addon.getSetting('us_proxy_pass') <> '' and addon.getSetting('us_proxy_user') <> '':
                      log('Using authenticated proxy: ' + us_proxy)
                      password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                      password_mgr.add_password(None, us_proxy, addon.getSetting('us_proxy_user'), addon.getSetting('us_proxy_pass'))
                      proxy_auth_handler = urllib2.ProxyBasicAuthHandler(password_mgr)
                      opener = urllib2.build_opener(proxy_handler, proxy_auth_handler)
                  else:
                      log('Using proxy: ' + us_proxy)
                      opener = urllib2.build_opener(proxy_handler)
              else:   
                  opener = urllib2.build_opener()
              urllib2.install_opener(opener)

              log("getRequest URL:"+str(url))
              req = urllib2.Request(url.encode(UTF8), user_data, headers)
              if doPut      == True: req.get_method = lambda: 'PUT'
              elif doDelete == True: req.get_method = lambda: 'DELETE'

              try:
                 response = urllib2.urlopen(req)
                 if response.info().getheader('Content-Encoding') == 'gzip':
                    log("Content Encoding == gzip")
                    buf = StringIO( response.read())
                    f = gzip.GzipFile(fileobj=buf)
                    link1 = f.read()
                 else:
                    link1=response.read()

              except urllib2.URLError, e:
                 if alert:
                     xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( __addonname__, e , 10000) )
                 link1 = ""

              if not (str(url).endswith('.zip')):
                 link1 = str(link1).replace('\n','')
              return(link1)



def getAutho():
              if addon.getSetting('login_name') != '':
                 vevoName     = addon.getSetting('login_name')
                 vevoPswd     = addon.getSetting('login_pass')
                 udata = urllib.urlencode({'username': vevoName, 'password':vevoPswd, 'grant_type':'password'})
              else:
                 udata = ' '

              azheaders = defaultHeaders
              azheaders['X-Requested-With'] = 'XMLHttpRequest'
              url   = VEVOBASE % '/auth'
              html  = getRequest(url, udata , azheaders)
              a = json.loads(html)
              return a["access_token"]


def getBase():
           html = getRequest(VEVOBASE % '/browse')
           blob = re.compile('config:(.+?)cdn:').search(html).group(1)
           blob = blob.strip(' ,')
           return json.loads(blob)


def getSources():
           a = getBase()
           ilist = []
           for name, url, mode in [(__language__(30060),VEVOAPI % '/tv/channels?withShows=true&hoursAhead=24&token=%s','GX'),
                                   (__language__(30061),VEVOAPI % '/now?page=1&size=%s&token=%s' % (str(maxitems),'%s'),'GD'),
                                   (__language__(30062),VEVOAPI % '/artists?page=1&size=%s' % str(maxitems),'GG'),
                                   (__language__(30063),VEVOAPI % '/videos?page=1&size=%s' % str(maxitems),'GG'),
                                   (__language__(30064),VEVOAPI % '/videos?page=1&size=%s&ispremiere=true&sort=MostRecent&token=%s' % (str(maxitems),'%s'),'GD'),
                                   (__language__(30065),VEVOAPI % '/videos?page=1&size=%s&islive=true&sort=MostRecent&token=%s'  % (str(maxitems),'%s'),'GD'),
                                   (__language__(30066), ' ', "GP"),
                                   (__language__(30067),VEVOAPI % '/videos?page=1&size=%s' % str(maxitems),'GQ')]:

              u = '%s?mode=%s&url=%s' %(sys.argv[0], mode, qp(url))
              liz=xbmcgui.ListItem(name, None , icon, icon)
              liz.setInfo( 'Video', { "Title": name })
              liz.setProperty('fanart_image', addonfanart)
              ilist.append((u, liz, True))
           xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))


def getChannels(curl):
              curl = uqp(curl).replace(' ','+')
              url = curl % getAutho()
              html = getRequest(url)
              a = json.loads(html)
              ilist =[]
              for b in a:
                  try:    img = b["thumbnailUrl"]
                  except: img = None
                  name = b["name"]
                  u  = b["stream"]
                  plot = b["description"]
                  liz=xbmcgui.ListItem( name, None , img, img)
                  liz.setInfo( 'Video', { "Title": name, "Plot" : plot })
                  liz.setProperty('fanart_image', addonfanart)
                  liz.setProperty('IsPlayable', 'true')
                  liz.setProperty('mimetype', 'video/x-msvideo')
                  ilist.append((u, liz, False))
              xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))


def getGenre(ggurl):
           a = getBase()
           ilist = []
           ggurl = uqp(ggurl).replace(' ','+')
           for b in a["browseCategoryList"]:
               if b["id"] != 'all': url = '%s&genre=%s' % (ggurl, b["id"])
               else: url = ggurl 
               name = b["loc"]
               u = '%s?mode=GS&url=%s' %(sys.argv[0], qp(url))
               liz=xbmcgui.ListItem(name, None , icon, icon)
               liz.setInfo( 'Video', { "Title": name })
               liz.setProperty('fanart_image', addonfanart)
               ilist.append((u, liz, True))
           xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))


def getSort(gsurl):
           a = getBase()
           ilist = []
           gsurl = uqp(gsurl).replace(' ','+')
           a = a["apiParams"]
           if '/artist' in gsurl: b = 'artist'
           else:  b = 'video'
           for x in a[b]["sort"]:
              name  = '%s - %s' % (b, a[b]["sort"][x])
              url = '%s&sort=%s&token=%s' % (gsurl, a[b]["sort"][x], '%s')
              u = '%s?mode=GD&url=%s' %(sys.argv[0], qp(url))
              liz=xbmcgui.ListItem(name, None , icon, icon)
              liz.setInfo( 'Video', { "Title": name })
              liz.setProperty('fanart_image', addonfanart)
              ilist.append((u, liz, True))
           xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))


def getArtist(durl):
              durl = uqp(durl).replace(' ','+')
              url = durl % getAutho()
              html = getRequest(url)
              blob = re.compile('"data"\:\{"videos"(.+?)\}\]\}\}\};').search(html).group(1)
              blob = '{"videos"'+blob
              try: a = json.loads(blob)
              except:
                blob = re.compile('"data"\:\{"videos"(.+?)\}\,\{"key').search(html).group(1)
                blob = '{"videos"'+blob
                a = json.loads(blob)
              loadData(durl.replace('/artist','/video',1),a)


def getQuery(url):
        keyb = xbmc.Keyboard('', __language__(30067))
        keyb.doModal()
        if (keyb.isConfirmed()):
              text = keyb.getText()
              qurl = qp(VEVOAPI % ('/search?q=%s&Limit=10&videosLimit=%s&skippedVideos=0&token=%s' % (text,str(maxitems), '%s')))
              getData(qurl)


def getNext(durl):
        try:
             pgex = re.compile('\?page=(.+?)&')
             pgn  = pgex.search(durl).group(1)
             pgnxt= '?page=%s&' % str(int(pgn)+1)
             url = pgex.sub(pgnxt, durl,1)
             u = '%s?mode=GD&url=%s' %(sys.argv[0], qp(url))
             liz=xbmcgui.ListItem( '[COLOR blue]%s[/COLOR]' % __language__(30068), None , icon, icon)
             liz.setProperty('fanart_image', addonfanart)
             return (liz,u)
        except:
             return (None, None)


def getData(durl):
              durl = uqp(durl).replace(' ','+')
              url = durl % getAutho()
              log( "GD url = "+str(url))
              html = getRequest(url, alert=False)
              try:
                a = json.loads(html)
                if '/search' in durl:
                   if len(a['videos']) == 0: raise ValueError('No Videos')
              except:
                 xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( __addonname__,__language__(30011)  , 5000) )
                 getSources()
                 return
              loadData(durl,a)


def loadData(durl,a, PlayList = None):
              ilist = []
              if ('/artist' in durl):
                if not ('/related' in durl) : a = a["artists"]
                for b in a:
                  name = b["name"]
                  url = VEVOBASE % ('/artist/%s?token=%s' % (b["urlSafeName"], '%s'))
                  try: img = b["thumbnailUrl"]
                  except:
                    try: img = b["image"]
                    except: img = None
                  artists =[]
                  artists.append(name)
                  u = '%s?mode=GA&url=%s' %(sys.argv[0], qp(url))
                  liz=xbmcgui.ListItem(name, None , img, img)
                  curl = VEVOAPI % ('/artist/%s/related?&size=%s&token=%s' % (b["urlSafeName"], str(maxitems), '%s'))
                  cm = [(__language__(30069),'XBMC.Container.Update(%s?mode=GD&url=%s)' % (sys.argv[0],qp(curl)))]
                  liz.addContextMenuItems(cm)
                  liz.setInfo( 'Video', { "Title": name, "Artist": artists })
                  liz.setProperty('fanart_image', addonfanart)
                  ilist.append((u, liz, True))
                if len(ilist) == maxitems:
                  liz,u = getNext(durl)
                  if liz != None: ilist.append((u, liz, True))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))
                return

              elif (('/video' in durl) and (not('/related' in durl))) or ('/search' in durl): a = a["videos"]
              elif '/now' in durl:   a = a["nowPosts"]
              fanart =''
              for c in a:
                  try: isrc = c["isrc"]
                  except:
                    try:  isrc = c["images"][0]["isrc"]
                    except:
                       log( "nothing found ....")
                       log( "c = "+str(c))
                       continue

                  try:  year  = c["year"]
                  except:
                    html = getRequest(VEVOAPI % ('/video/%s?token=%s' % (isrc, getAutho())))
                    c = json.loads(html)
                    year  = c["year"]

                  name = c['title']
                  try:    img = c["thumbnailUrl"]
                  except: img = None
                  try:    fanart = c["artists"][0]["thumbnailUrl"]
                  except:
                    try:    fanart = c['image']
                    except: fanart = addonfanart

                  artists = []
                  for x in c["artists"]: artists.append(x["name"])
                  album = artists[0]

                  url   = VEVOAPI % ('/video/%s/streams/hls?token=' % isrc)
                  vname = '%s - %s' % (album, name)
                  u = '%s?mode=GV&url=%s' %(sys.argv[0], qp(url))
                  liz=xbmcgui.ListItem( vname , None , img, img)
                  if PlayList != None:
                     cm = [(__language__(30070),'XBMC.Container.Update(%s?mode=RP&url=%s&puid=%s)' % (sys.argv[0],isrc, PlayList))]
                  else:
                     cm = [(__language__(30071),'XBMC.RunPlugin(%s?mode=AP&url=%s)' % (sys.argv[0],isrc))]

                  curl = VEVOAPI % ('/video/%s/related?&size=%s&token=%s' % (isrc, str(maxitems), '%s'))
                  cm.append((__language__(30069),'XBMC.Container.Update(%s?mode=GD&url=%s)' % (sys.argv[0],qp(curl))))
                  liz.addContextMenuItems(cm)
                  liz.setInfo( 'Video', { "Title": name, "Artist": artists, "Year" : year, "Album": album })
                  liz.setProperty('fanart_image', fanart)
                  liz.setProperty('IsPlayable', 'true')
                  liz.setProperty('mimetype', 'video/x-msvideo')
                  ilist.append((u, liz, False))
              if len(ilist) == maxitems:
                  liz,u = getNext(durl)
                  if liz != None: ilist.append((u, liz, True))
              xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))

def getVideo(caturl):
              url  = '%s%s' % (uqp(caturl), getAutho())
              html = getRequest(url)
              a    = json.loads(html)
              for b in a:
                if b["version"] == 2:
                   liz = xbmcgui.ListItem(path = b["url"])
                   xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)

def getMe(token):
              url  = VEVOAPI % ('/me?token=%s' % token)
              html = getRequest(url)
              a = json.loads(html)
              try: uid = a['id']
              except: uid = None
              return uid

def getPlaylists():
              if addon.getSetting('login_name') == '':
                   addon.openSettings()
                   getSources()
                   return
              token = getAutho()
              uid = getMe(token)
              html = getRequest(VEVOAPI % ('/user/%s/playlists?token=%s' % (uid,token)))
              a = json.loads(html)
              ilist=[]
              for b in a:
                  try:    img = b["thumbnailUrl"]
                  except: img = None
                  name = b["name"]
                  plot = b["description"]
                  u = '%s?mode=GL&url=%s' %(sys.argv[0], qp(b["playlistId"]))
                  liz=xbmcgui.ListItem( name, None , img, img)
                  cm = [(__language__(30072),'XBMC.Container.Refresh(%s?mode=DP&url=%s)' % (sys.argv[0], b["playlistId"])),
                        (__language__(30075),'XBMC.Container.Refresh(%s?mode=RL&url=%s)' % (sys.argv[0], b["playlistId"]))]
                  liz.addContextMenuItems(cm)
                  liz.setInfo( 'Video', { "Title": name, "Plot" : plot })
                  liz.setProperty('fanart_image', addonfanart)
                  ilist.append((u, liz, True))

              u = '%s?mode=CP' %(sys.argv[0])
              liz=xbmcgui.ListItem( __language__(30073), None , icon, icon)
              liz.setInfo( 'Video', { "Title": name })
              liz.setProperty('fanart_image', addonfanart)
              ilist.append((u, liz, True))
              xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))

def getList(puid):
              html = getRequest(VEVOAPI % ('/playlist/%s?token=%s' % (puid, getAutho())))
              a = json.loads(html)
              loadData('/videos', a, PlayList = puid)

def createList():
        keyb = xbmc.Keyboard('', __language__(30074))
        keyb.doModal()
        if (keyb.isConfirmed()):
              text = keyb.getText()
              udata = 'name=%s&Isrcs=undefined' % qp(text)
              url = VEVOAPI % ('/me/playlists?token=%s' % getAutho())
              azheaders = defaultHeaders
              azheaders['X-Requested-With'] = 'XMLHttpRequest'
              getRequest(url, udata, azheaders)
        getPlaylists()


def deleteList(puid):
         url = VEVOAPI % ('/me/playlist/%s?token=%s') % (puid, getAutho())
         azheaders = defaultHeaders
         azheaders['X-Requested-With'] = 'XMLHttpRequest'
         getRequest(url, ' ', azheaders, doDelete=True )
         getPlaylists()

def renameList(puid):
        html = getRequest(VEVOAPI % ('/playlist/%s?token=%s' % (puid, getAutho())))
        a = json.loads(html)
        oldname = a["name"]
        keyb = xbmc.Keyboard(oldname, __language__(30075))
        keyb.doModal()
        if (keyb.isConfirmed()):
              newname = keyb.getText()
              if len(newname) > 0: 
                 updateList(puid, name=newname)
                 getPlaylists()
         
def getListID():
              token = getAutho()
              uid = getMe(token)
              html = getRequest(VEVOAPI % ('/user/%s/playlists?token=%s' % (uid,token)))
              a = json.loads(html)
              ilist=[]
              nlist=[]
              for b in a:
                nlist.append(b['name'])
                ilist.append(b['playlistId'])
              dialog = xbmcgui.Dialog()
              choice = dialog.select('Choose a playlist', nlist)
              return ilist[choice]


def addtoList(isrc):
              puid = getListID()
              updateList(puid, doAdd=isrc)
              cod = False

def delfmList(puid, isrc):
              updateList(puid, doDel=isrc)
              getList(puid)
              

def updateList(puid, name = None, desc = None, doAdd = None, doDel = None, imageUrl = None):
              token = getAutho()
              html = getRequest(VEVOAPI % ('/playlist/%s?token=%s' % (puid, token)))
              a = json.loads(html)
              ud = 'playlistId=%s' % qp(puid)
              if name == None : name = a['name']
              ud += '&name=%s' % qp(name)
              if desc == None : desc = a['description']
              ud += "&description=%s" % qp(desc)
              if imageUrl == None: imageUrl = a['imageUrl']
              ud += "&imageUrl=%s" % qp(imageUrl)
              b = a["videos"]
              for c in b:
                 if c['isrc'] == doDel: continue
                 else: ud += "&Isrcs=%s" % qp(c['isrc'])
              if doAdd != None : ud += "&Isrcs=%s" % qp(doAdd)
              udata = ud
              azheaders = defaultHeaders
              azheaders['X-Requested-With'] = 'XMLHttpRequest'
              url = VEVOAPI % ('/me/playlist/%s?token=%s' % (puid, token))
              html  = getRequest(url, udata , azheaders, doPut=True)



# MAIN EVENT PROCESSING STARTS HERE


parms = {}
try:
    parms = dict( arg.split( "=" ) for arg in ((sys.argv[2][1:]).split( "&" )) )
    for key in parms: parms[key] = demunge(parms[key])
except:  parms = {}

p = parms.get
try:    mode = p('mode')
except: mode = None

if (mode != 'AP'): xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')

if mode==  None:  getSources()
elif mode=='GX':  getChannels(p('url'))
elif mode=='GA':  getArtist(p('url'))
elif mode=='GG':  getGenre(p('url'))
elif mode=='GS':  getSort(p('url'))
elif mode=='GD':  getData(p('url'))
elif mode=='GV':  getVideo(p('url'))
elif mode=='GQ':  getQuery(p('url'))
elif mode=='GP':  getPlaylists()
elif mode=='GL':  getList(p('url'))
elif mode=='AP':  addtoList(p('url'))
elif mode=='RP':  delfmList(p('puid'), p('url'))
elif mode=='CP':  createList()
elif mode=='DP':  deleteList(p('url'))
elif mode=='RL':  renameList(p('url'))

if (mode !='AP'): xbmcplugin.endOfDirectory(int(sys.argv[1]))
