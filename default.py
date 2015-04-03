# -*- coding: utf-8 -*-
# VEVO Addon

import sys
import httplib
import urllib, urllib2, cookielib, datetime, time, re, os, string
import xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, xbmc
import cgi, gzip
from StringIO import StringIO
import json


USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
UTF8          = 'utf-8'

VEVOBASE = 'http://www.vevo.com%s'
VEVOAPI  = 'https://apiv2.vevo.com%s'

addon         = xbmcaddon.Addon('plugin.video.myvevo')
__addonname__ = addon.getAddonInfo('name')
__language__  = addon.getLocalizedString

qp  = urllib.quote_plus
uqp = urllib.unquote_plus

home          = addon.getAddonInfo('path').decode(UTF8)
icon          = xbmc.translatePath(os.path.join(home, 'icon.png'))
addonfanart   = xbmc.translatePath(os.path.join(home, 'fanart.jpg'))


def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def cleanname(name):    
    return name.replace('<p>','').replace('<strong>','').replace('&apos;',"'").replace('&#8217;',"'")

def demunge(munge):
        try:    munge = urllib.unquote_plus(munge).decode(UTF8)
        except: pass
        return munge

USER_AGENT    = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36'
defaultHeaders = {'User-Agent':USER_AGENT, 
                 'Accept':"text/html,application/xhtml+xml,application/xml,application/json;q=0.9,image/webp,*/*;q=0.8", 
                 'Accept-Encoding':'gzip,deflate,sdch',
                 'Accept-Language':'en-US,en;q=0.8'} 

def getRequest(url, user_data=None, headers = defaultHeaders , alert=True):

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
              azheaders = defaultHeaders
              azheaders['X-Requested-With'] = 'XMLHttpRequest'
              url = VEVOBASE % '/auth'
              html = getRequest(url, '' , azheaders)
              a = json.loads(html)
              return a["access_token"]


def getBase():
           html = getRequest(VEVOBASE % '/browse')
           blob = re.compile('config:(.+?)cdn:').search(html).group(1)
           blob = blob.strip(' ,')
           return json.loads(blob)


def getSources(fanart):
           a = getBase()
           ilist = []
           for name, url, mode in [("VEVO TV",VEVOAPI % '/tv/channels?withShows=true&hoursAhead=24&token=%s','GX'),
                                   ("Artists",VEVOAPI % '/artists?page=1&size=25','GG'),
                                   ("Videos",VEVOAPI % '/videos?page=1&size=25','GG'),
                                   ("Premieres",VEVOAPI % '/videos?page=1&size=25&ispremiere=true&sort=MostRecent&token=%s','GD'),
                                   ("Live Performances",VEVOAPI % '/videos?page=1&size=25&islive=true&sort=MostRecent&token=%s','GD'),
                                   ("Search",VEVOAPI % '/videos?page=1&size=25','GQ')]:
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
           else:                  b = 'video'
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
        keyb = xbmc.Keyboard('', __addonname__)
        keyb.doModal()
        if (keyb.isConfirmed()):
              text = keyb.getText()
              qurl = qp(VEVOAPI % ('/search?q=%sLimit=6&videosLimit=25&skippedVideos=0&token=%s' % (text, '%s')))
              getData(qurl)


def getData(durl):
              durl = uqp(durl).replace(' ','+')
              url = durl % getAutho()
              html = getRequest(url)
              a = json.loads(html)
              loadData(durl,a)


def loadData(durl,a):
              ilist = []
              if '/artist' in durl:
                a = a["artists"]
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
                  liz.setInfo( 'Video', { "Title": name, "Artist": artists })
                  liz.setProperty('fanart_image', addonfanart)
                  ilist.append((u, liz, True))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))
                return

              elif '/video' in durl:  a = a["videos"]
              elif '/now' in durl:   a = a["nowPosts"]
              fanart =''
              for c in a:
                  try: isrc = c["isrc"]
                  except:
                    try:  isrc = c["images"][0]["isrc"]
                    except:
                       print "nothing found ...."
                       print "c = "+str(c)
                       continue

                  try:  year  = c["year"]
                  except:
                    html = getRequest(VEVOAPI % ('/video/%s?token=%s' % (isrc, token)))
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

                  url  = VEVOAPI % ('/video/%s/streams/hls?token=' % isrc)
                  u = '%s?mode=GV&url=%s' %(sys.argv[0], qp(url))
                  liz=xbmcgui.ListItem( '%s - %s' % (album, name), None , img, img)
                  liz.setInfo( 'Video', { "Title": name, "Artist": artists, "Year" : year, "Album": album })
                  liz.setProperty('fanart_image', fanart)
                  liz.setProperty('IsPlayable', 'true')
                  liz.setProperty('mimetype', 'video/x-msvideo')
                  ilist.append((u, liz, False))
              xbmcplugin.addDirectoryItems(int(sys.argv[1]), ilist, len(ilist))

def getVideo(caturl):
              url  = '%s%s' % (uqp(caturl), getAutho())
              html = getRequest(url)
              a    = json.loads(html)
              for b in a:
                if b["version"] == 2:
                   xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, xbmcgui.ListItem(path = b["url"]))



# MAIN EVENT PROCESSING STARTS HERE

xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')

parms = {}
try:
    parms = dict( arg.split( "=" ) for arg in ((sys.argv[2][1:]).split( "&" )) )
    for key in parms: parms[key] = demunge(parms[key])
except:  parms = {}

p = parms.get
try:    mode = p('mode')
except: mode = None

if mode==  None:  getSources(p('fanart'))
elif mode=='GX':  getChannels(p('url'))
elif mode=='GA':  getArtist(p('url'))
elif mode=='GG':  getGenre(p('url'))
elif mode=='GS':  getSort(p('url'))
elif mode=='GD':  getData(p('url'))
elif mode=='GV':  getVideo(p('url'))
elif mode=='GQ':  getQuery(p('url'))

xbmcplugin.endOfDirectory(int(sys.argv[1]))
