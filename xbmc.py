#! /usr/bin/env python2.7
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 saja <saja@saja-lap>
#
# Distributed under terms of the MIT license.

from __future__ import print_function
import requests
import argparse
import json
import re
import os
import subprocess

"""
Kodi client writte in python
"""

default_host = "127.0.0.1"

class Kodi:
    def __init__ (self,host,port="8080",user=None , password=None , verbose=0):
        self.url  = "http://" + host + ":" + port + "/jsonrpc"
        self.host = host
        self.verbose = verbose
        self.playerid = 1
        # r = requests.post(self.url, json= {"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 99})
        r = self.send_command ( method = "Player.GetActivePlayers" , id = "99" )
        try:
            self.activePlayer = r
            self.playerid = r[0]["playerid"]
        except:
            self.playerid = 1 

    def get_host (self):
        if ( self.verbose >= 1 ):
            print ( "Get host %s" % self.host )
        return ( self.host)

    def set_host (self,host_new):
        if ( self.verbose >= 1 ):
            print ( "Set host to %s" % host_new )
        host = host_new 

    def set_verbosity (self,num):
        self.verbose = int(num)

    def send_command(self,method="" , id = "1" ,params={}):
        """
        Send command to kodi
        """
        data = {"jsonrpc": "2.0", "method": method ,  "params" : params , "id": self.playerid } 
        r = requests.post(self.url, json=data)
        if ( self.verbose >= 2 ):
            print ( "\nmethod = \"%s\"\ndata = %s\nurl = \"%s\"" % ( str(method) , str(data) , str(self.url)))
            print ( "result = requests.post (url , json = data)" )
            print ( "status = %s" % str(r.status_code))
            print ( "text   = %s" % str(r.text))

        if [ r.text ]:
            return (json.loads(r.text)["result"])
        else:
            return ""

    def play(self,open_item,queue=False):
        enums = { "next" : self.next,
                  "prev" : self.prev,
                  "first": self.first,
                  "last" : self.last,
                  }
        # no argumant passed
        if ( open_item == "-1" ):
            self.play_pause()
            return

        # 1,2,3,...
        try:
            i = int(open_item)
            if ( self.verbose >= 1 ):
                print ("Jump to %ith in playlist" % i )
            self.send_command ( method = "Player.GoTo" , params = {"playerid" : self.playerid , "to" : i })
        except:
            # next , prev , last ,end
            if (open_item in enums.keys()):
                if ( self.verbose >= 1 ):
                    print ( "%s is in enum" % open_item)
                enums[open_item]()
                return

            pattern = re.compile ( r'.*youtube.*?v.?=(.{11})')
            item = pattern.search(open_item)
            # https://www.youtube.com/
            if item:
                yt_id = item.group(1)
                files = self.search_db(yt_id , ext="mp4")
                if (self.verbose >= 1 ):
                    print ("Playing youtube: %s"  % yt_id )
                if files:
                    r = self.send_command( method = "Player.Open" , params = {"item" : { "file" : files[0]}})
                else:
                    r = self.send_command ( method = "Playlist.GetItems" , params = { "playlistid" : self.playerid , "properties" : ["title"] , "limits" : { "start" : 0 , "end" : 100 } } )
                    if "items" not in r.keys():
                        i = 0 
                    else:
                        i = r["limits"]["end"]
                    self.send_command( method = "Playlist.Add" , params = {"playlistid":self.playerid, "item" :{ "file" : "plugin://plugin.video.youtube/?action=play_video&videoid={0}".format(yt_id)}})
                    if not queue:
                        self.send_command( method = "Player.Open" , params = {"item":{"playlistid":self.playerid, "position" : i}})
            # none
            else:
                files = self.search_db (open_item )
                r = self.send_command ( method = "Playlist.GetItems" , params = { "playlistid" : self.playerid , "properties" : ["title"] , "limits" : { "start" : 0 , "end" : 100 } } )
                if "items" not in r.keys():
                    i = 0 
                else:
                    i = r["limits"]["end"]
                if files:
                    for f in files:
                        self.send_command(method="Playlist.Add" , params = {"playlistid" : self.playerid , "item" :{ "file" : f}})
                    if not queue:
                        self.send_command( method = "Player.Open" , params = {"item":{"playlistid":self.playerid, "position" : i}})


    def search_local_db ( self , query , db_type="Songs" ):
        if ( db_type is not "Songs"):
            print ( "Other databases not available")
            return 
        else:
            print ( "Searching for " + str(query))
            r = self.send_command ( method = "AudioLibrary.GetSongs" , params = {"properties" : ["file" , "artistid"] , "filter" : {"field" : "title" , "operator" : "contains" , "value" : query }}) 
            print(r)

    def search_db (self ,query , ext=""):
        pattern = re.compile ("(.*)(mp3|mp4|avi|mkv|m3u)$")
        a = pattern.search(query)
        if a:
            query = a.group(1)
            ext = a.group(2)
        else:
            ext = "(mp3|mp4|avi|mkv|m3u)"
        if (self.verbose >= 1):
            print ( "searching local database for: %s.*%s" % (query,ext) )
        db1_path = os.path.join ( os.environ["src"] , "lists/HDD.db")
        locate_command = "/usr/bin/locate"
        (files , err ) = subprocess.Popen ([locate_command  , "--regex" , "-i" , "-d" , db1_path , query+ ".*" + ext ] ,stdout=subprocess.PIPE).communicate()
        if files:
            # files = [i for i in files.splitlines() if  not "workspace" in i ]
            # for SMB Shared dir
            if (self.host == "127.0.0.1"):
                files = [i.replace("/media/HDD", "smb://192.168.1.135/HDD_DIR") for i in files.splitlines() if  not "workspace" in i ]
            elif (self.host == "192.168.1.135"):
                files = [i for i in files.splitlines() if  not "workspace" in i ]

            if (self.verbose >= 1):
                print(files)
            return(files)

    def play_pause (self):
        if ( self.verbose >= 1 ):
            print ("Play or pause")
        self.send_command ( method = "Player.PlayPause" ,params = { "playerid" : self.playerid})
        
    def stop (self):
        if ( self.verbose >= 1 ):
            print ("Stop")
        self.send_command ( method = "Player.Stop" , params = { "playerid" : self.playerid })
        self.send_command ( method = "Playlist.Clear" , params = { "playlistid" : self.playerid })

    def volume_up (self):
        if ( self.verbose >= 1 ):
            print ( "Volume up")
        self.send_command ( method = "Application.SetVolume" ,params = { "volume": "increment" })

    def volume_down(self):
        if ( self.verbose >= 1 ):
            print ( "Voluem down")
        self.send_command ( method = "Application.SetVolume" ,params = { "volume": "decrement" })

    def seek_forward (self):
        if ( self.verbose >= 1 ):
            print ( "Seek forward" )
        self.send_command ( method = "Player.Seek" ,params = {"playerid" : self.playerid , "value":"smallforward" })

    def seek_backward (self):
        if ( self.verbose >= 1 ):
            print ( "Seek backward" )
        self.send_command ( method = "Player.Seek" ,params = {"playerid" : self.playerid , "value":"smallbackward" })

    def next (self):
        if ( self.verbose >= 1 ):
            print ("Next")
        self.send_command ( method = "Player.GoTo" , params = {"playerid" : self.playerid , "to" : "next" })

    def prev (self):
        if ( self.verbose >= 1 ):
            print ( "Previous")
        self.send_command ( method = "Player.GoTo" , params = {"playerid" : self.playerid , "to" : "previous" })
    
    def first (self):
        if ( self.verbose >= 1 ):
            print ( "First")
        self.send_command ( method = "Player.GoTo" , params = {"playerid" : self.playerid , "to" : 0 })
    
    def last (self):
        if ( self.verbose >= 1 ):
            print ( "Last")
        self.send_command ( method = "Player.GoTo" , params = {"playerid" : self.playerid , "to" : 100 })
    
    def repeat (self):
        if ( self.verbose >= 1 ):
            print ( "Repeat cycle")
        self.send_command ( method = "Player.SetRepeat" , params = {"playerid" : self.playerid , "repeat" : "cycle" })

    def shuffle (self):
        if ( self.verbose >= 1 ):
            print ( "Shuffle")
        self.send_command ( method = "Player.SetShuffle" , params = {"playerid" : self.playerid , "shuffle" : "toggle" })

    def rate (self,number):
        if ( self.verbose >= 1 ):
            print ( "Set rating to {0}".format(number))
        r = self.send_command ( method = "Player.GetItem" , params = { "playerid" : self.playerid , "properties" : ["title" , "artist" ,  "file" , "userrating" , "rating" , "uniqueid" ]})
        if "id" in r["item"].keys:
            dbid = r["item"]['id']
        else:
            path   = r["item"]["file"]
            title  = r["item"]["title"]
            try:
                artist = r["item"]["artist"][0]
                rating = r["item"]["userrating"]
            except:
                year = 0
                rating = 0
                artist = ""
            r = send_command ( method = "AudioLibrary.GetArtists" , params = {"properties" : [] , "filter" : {"field" : "artist" , "operator" : "is" , "value" : artist }})
            if [ not "artists" in r.keys() ]:
                return
            else:
                artistID = r["artists"][0]["artistid"]
                r = send_command ( method = "AudioLibrary.GetSongs" , params = {"properties" : ["file" , "artistid"] , "filter" : {"field" : "artist" , "operator" : "contains" , "value" : artist }}) 
                f = r["item"]['file']
                dbid = r["item"]['file']
            self.send_command ( method = "AudioLibrary.SetSongDetails" , params = { "songid" : dbid , "userrating" : number })

    def audio_profile(self,profile_id):
        if ( self.verbose >= 1 ):
            print ( "Audio profile to %i" % profile_id )
        print ( "set audio profile to %i" % profile_id  if self.verbose >= 1 else "")
        self.send_command ( method = "Addons.ExecuteAddon" , params = {"addonid":"script.audio.profiles","params": str(profile_id) } )
        self.send_command ( method = "AudioLibrary.GetSongs" , params = {"properties" : ["file" , "artistid"] , "filter" : {"field" : "path" , "operator" : "contains" , "value" : path }})

    def scan_audioLibrary(self):
        if ( self.verbose >= 1 ):
            print ( "Scan audio library" )
        self.send_command ( method = "AudioLibrary.Scan" )

    def scan_videoLibrary(self):
        if ( self.verbose >= 1 ):
            print ( "Scan video library" )
        self.send_command ( method = "VideoLibrary.Scan" )

    def addonTrakt(self):
        if ( self.verbose >= 1 ):
            print ("Start Trakt")
        self.send_command ( method = "Addons.ExecuteAddon" , params = {"addonid":"script.trakt"} )

    def deletNowPlaying(self):
        if ( self.verbose >= 1 ):
            print ( "Delete now playing")
        self.send_command ( method = "Addons.ExecuteAddon" , params = {"addonid":"script.delete.playing"} )

    def full_screen(self):
        if ( self.verbose >= 1 ):
            print ( "FullScreen" )
        self.send_command ( method = "GUI.SetFullscreen" , params = {"fullscreen": "toggle"} )

    def add_to_favorite(self):
        r = self.send_command ( method = "Player.GetItem" , params = {"playerid" : self.playerid , "properties" : [ "file" , "title" ] } )
        label = r ["item"]["label"].replace("_", " ").replace(".mp4" ,"").replace (".mp3" ,"")
        if ( self.verbose >= 1 ):
            print ( "Adding %s to favorites" % label )
        self.send_command ( method = "Favourites.AddFavourite" , params = {"title" : label , "type" : "media" , "path" : r["item"]["file"]})

    def show_info(self):
        def print_time (done_time , total_time ):
            if total_time["hours"] == 0:
                return str( "%02i:%02i/%02i:%02i" % ( done_time["minutes"], done_time["seconds"] , total_time["minutes"] , total_time["seconds"] ))
            else:
                return str( "%02i:%02i:%02i/%02i:%02i:%02i" % ( done_time["hours"] , done_time["minutes"], done_time["seconds"] ,total_time["hours"] , total_time["minutes"] , total_time["seconds"] ))
        
        def print_percent ( percent ):
            i = int(percent)
            j = 10 - i
            # Green Printing
            print ( i * "\033[1;32m>" + (10-i) * "\033[m=")

        if len(self.activePlayer) == 0:
            return
        media_type  = self.activePlayer[0]["type"]

        r = self.send_command ( method = "Application.GetProperties" , params = { "properties" : ["volume"]})
        volume = r["volume"]

        r = self.send_command ( method = "Playlist.GetProperties" , params = { "playlistid" : self.playerid ,  "properties" : ["type" , "size"]})
        playlist_size = r["size"]

        self.playerProperties = self.send_command ( method = "Player.GetProperties" , params = { "playerid" : self.playerid , "properties" : ["totaltime" , "time" , "playlistid" , "percentage" , "position" , "repeat" , "shuffled" , "live" ,"canseek" , "canzoom" , "speed" ]} )
        percentage = self.playerProperties["percentage"]
        playing  = self.playerProperties["speed"]
        done_time  = self.playerProperties["time"]
        total_time  = self.playerProperties["totaltime"]
        repeat = self.playerProperties["repeat"]
        shuffle = self.playerProperties["shuffled"]
        position = self.playerProperties["position"]

        r = self.send_command ( method = "Player.GetItem" , params = { "playerid" : self.playerid , "properties"     : ["title" , "artist" , "duration" , "runtime" , "file" , "userrating" , "year" , "rating" , "uniqueid" , "director" , "imdbnumber" ,"season", "episode", "showtitle" , "plot" , "firstaired" ]} )
        path   = r["item"]["file"]
        title  = r["item"]["title"]
        try:
            year   = r["item"]["year"]
            rating = r["item"]["userrating"]
        except:
            year = 0
            rating = 0

        if ( media_type  == "audio" ):
            try:
                artist = r["item"]["artist"][0]
            except:
                artist = ""
            print ( "♫ ♫ ♫ ♫ ♫" )
            print ( "%s - %s\t\t" % ( artist , title ),end="")
            print ( "\trate:(" + rating * "\033[1;31m*\033[m" + ")" )
            print ( "[Playing]" if playing == 1 else "[Paused]" , end = "" )    
            print ( "\t#%i/%i" % (position , playlist_size ) ,end = "" )
            print ( "\t%s" % ( print_time ( done_time , total_time )) , end ="")
            print ( "\t(%%%i)\tyear:(%s)"  % (percentage,year ))
            print ( "volume: %i\trepeat: %s\t shuffle: %s" % (volume,repeat,shuffle))
            print ( "\"https://www.last.fm/user/sajjadzamani/library/music/%s/_/%s\"" % (artist.replace(" ","+")  , title.replace(" ","+")))
            print ( "\"https://www.musixmatch.com/lyrics/%s/%s\""                     % (artist.replace(" ","-")  , title.replace(" ","-").replace("'","-")))

            if ( self.verbose >= 1 ):
                print_percent ( percentage )
            
        elif ( media_type  == "video" ):
            video_type = r["item"]["type"]
            print ( "📺📺📺📺📺" )

            if (video_type == "episode" ):
                plot   = r["item"]["plot"]
                episode    = r["item"]["episode"]
                season     = r["item"]["season"]
                firstaired = r["item"]["firstaired"]
                show_title = r["item"]["showtitle"]
                print ( "%s - %s" % (show_title , title ))
                print ( "[Playing]\t" if playing == 1 else "[Paused]\t" , end = "" )
                print ( "%s" % ( print_time ( done_time , total_time )) , end ="")
                print ( "\t(%%%i)\t(S%02i%02i)"  % (percentage , season,episode))
                print ( "volume: %i\trepeat: %s\t shuffle: %s" % (volume,repeat,shuffle))
                if (self.verbose >= 1 ):
                    print (str( "\"https://trakt.tv/shows/%s/seasons/%i/episodes/%i\"" % (show_title , season, episode)).replace(" ","-"))
                    print_percent ( percentage )
                    print (plot)

            elif ( video_type == "movie" ):
                plot   = r["item"]["plot"]
                print ( "%s - %s" % (title , year ))
                print ( "[Playing]\t" if playing == 1 else "[Paused]\t" , end = "" )
                print ( "%s\t" % ( print_time ( done_time , total_time )) , end ="")
                print ( "\t(%%%i)\t"  % (percentage ))
                print ( "\t(" + rating * "\033[1;31m*\033[m" + ")" )
                print ( "volume: %i\trepeat: %s\t shuffle: %s" % (volume,repeat,shuffle))
                if (self.verbose >= 1 ):
                    print ( "\"https://trakt.tv/movies/%s-%i\"" %( title.replace(" ","-") , year))
                    print_percent ( percentage )
                    print (plot)

            else:
                label = r["item"]["label"]
                file_path = r["item"]["file"]
                # label = (20180215)-Vox-How_figure_skaters_choose_their_music_explained_with_Adam_Rippon-(VA_P3p7MI98).mp4
                pattern = re.compile ( r'\((.*?)\)-(.*)-\((.*?)\)\.(.*)') 
                item  = pattern.search (label)
                if item:
                    yt_id = item.group(3)
                    year  = item.group(1)
                    title = item.group(2).replace("_" , " ")
                else:
                    yt_id = ""
                    year  = "0000"
                    title = label

                print ( "%s" % ( title ))
                print ( "[Playing]\t" if playing == 1 else "[Paused]\t" , end = "" )
                print ( "#%i/%i\t" % (position , playlist_size ) ,end = "" )
                print ( "%s\t" % ( print_time ( done_time , total_time )) , end ="")
                print ( "(%%%i)\t"  % (percentage ))
                print ( "volume: %i\trepeat: %s\t shuffle: %s" % (volume,repeat,shuffle))
                if (self.verbose >= 1 ):
                    if ( yt_id) :
                        print ( "\"https://www.youtube.com/watch?v=%s\"" % yt_id )
                    print ( file_path )
                    print_percent ( percentage )


    def get_input (self):
        if ( self.verbose >= 1 ):
            print ("Get input from keyboard" )
            print ("Needs a lot of work")

        def getchar():
            #Returns a single character from standard input
            import tty, termios, sys
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch
            
        while True:
            ch = getchar()
            print ( 'You pressed %c'% ch)

    def show_playlist (self,limit=10):
        try:
            position = self.playerProperties["position"]
        except:
            quit()
        

        r = self.send_command ( method = "Playlist.GetItems" , params = { "playlistid" : self.playerid , "properties" : ["title"] , "limits" : { "start" : max (position - limit , 0) , "end" : position + limit } } )
        if "items" not in r.keys():
            print ( "Nothing playing")
            return

        i = max (position-limit , 0)
        for item in r["items"]:
            if ( i == position ):
                if ( item["type"] == "song" and "id" in item.keys()):
                    # print ( "%02i-> \033[1;32m%s\033[m" % (i , item["label"]))
                    # self.send_command (method = "AudioLibrary.GetSongDetails" , params = { "songid" : item["id"]})
                    print ("...")
                else:
                    print ( "%02i-> \033[1;32m%s\033[m" % (i , item["label"]))
            else:
                if ( item["type"] == "song" and "id" in item.keys()):
                    print ( "%02i-> %s" % ( i , item["label"]))
                else:
                    print ( "%02i-> %s" % ( i , item["label"]))
            i = i +1
        return (r["limits"]["end"])

    def test(self):
        if ( self.verbose >= 1 ):
            print ("Test")
        r = self.send_command ( method = "AudioLibrary.GetSongDetails", params={'songid': 5108 , 'properties': ['title' , 'artist' , 'thumbnail' , 'userrating']}) 


    def sample(self):
        if ( self.verbose >= 1 ):
            print ("Sample")
        r = self.send_command ( method = "" , params = {""} )

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Kodi commands")

    parser.add_argument ("-H" , "--host" , nargs="?" , help="Set the host ip")
    group_options = parser.add_argument_group()
    group_options.add_argument("-v","--verbose",default=1,action="count",help="level of verbosity")

    group_commands = parser.add_mutually_exclusive_group()
    # group_commands.add_argument("-p","--play",action="store_true",help="Play or pause")
    group_commands.add_argument("-s","--stop",action="store_true",help="Stop")
    group_commands.add_argument("--clear"     ,action="store_true",help="Stop")
    group_commands.add_argument("-u","--up"  ,action="store_true",help="Volume up" , dest="volumeUp")
    group_commands.add_argument("-d","--down",action="store_true",help="Voluem down",dest="volumeDown")
    group_commands.add_argument("-j","--forward",action="store_true",help="seek forward")
    group_commands.add_argument("-k","--backward",action="store_true",help="seek backward")
    group_commands.add_argument("-J","--next",action="store_true",help="Next item")
    group_commands.add_argument("-K","--prev",action="store_true",help="Prev item")
    group_commands.add_argument("--repeat",action="store_true",help="Repeat playlist")
    group_commands.add_argument("--shuffle",action="store_true",help="Toggle shuffle")
    group_commands.add_argument("-S", "--search",help="Search database")
    group_commands.add_argument("--rate",choices = ['0','1','2','3','4','5','6','7','8','9','10'],help="Set rating")

    group_open = parser.add_argument_group ()
    group_open.add_argument ( "-p","--play",action="append" , nargs="?",const="-1" , help = "Play" )
    group_open.add_argument ( "-q","--queue",action="append" , nargs="?",const="-1" , help = "Queue" )
    # group_open.add_argument ( "-q","--queue"   , nargs="+" , help="Queue media")
    # group_open.add_argument ( "-y","--youtube" , nargs="+" , help="Play youtube videos")
    # group_open.add_argument ( "-o","--open"    , nargs="+" , help="Local videos")


    group_audioAddons = parser.add_mutually_exclusive_group()
    group_audioAddons.add_argument ("-1" , action="store_true",help="Audio HDMI" ,dest = "audio1")
    group_audioAddons.add_argument ("-2" , action="store_true",help="Audio 3.5"  ,dest = "audio2" )
    group_audioAddons.add_argument ("-3" , action="store_true",help="Audio both" ,dest = "audio3")
    group_audioAddons.add_argument ("--audio" , choices = ["3.5" , "hdmi" , "both" ] ,help="Audio select")

    parser.add_argument ("-A" , "--scanAudio" , action="store_true" , help = "Scan audio library" )
    parser.add_argument ("-V" , "--scanVideo" , action="store_true" , help = "Scan video library" )
    parser.add_argument ("-T" , "--trakt"     , action="store_true" , help = "Run trakt" )
    parser.add_argument ("-D" , "--delete"    , action="store_true" , help = "Delete now playing" )
    parser.add_argument ("-F" , "--fullScreen", action="store_true" , help = "Fullscreen" )
    parser.add_argument ("-f" , "--fave"      , action="store_true" , help = "Favorites" )

    # parser.add_argument ("-I" , "--info"      , action="store_true" , help = "Show info of now playing file" )
    parser.add_argument ( "--playlist"        , action="store_true" , help = "Show now playing playlist" )
    parser.add_argument ("-i" , "--input"     , action="store_true" , help = "Send keystrokes to kodi" )
    parser.add_argument ("-Z" , "--test"      , action="store_true" , help = "Test function" )

    args = parser.parse_args()
    if args.host:
        k = Kodi(verbose=args.verbose,host=args.host)
    else:
        k = Kodi(verbose=args.verbose,host=default_host)


    # if(args.verbose >= 2 ):
        # print(args)

    if args.play:
        k.play(args.play[0])

    if args.queue:
        k.play(args.queue[0],queue=True)

    if args.stop or args.clear:
        k.stop()
        quit()

    if args.volumeUp:
        k.volume_up()

    if args.volumeDown:
        k.volume_down()

    if args.forward:
        k.seek_forward()

    if args.backward:
        k.seek_backward()

    if args.next:
        k.next()

    if args.prev:
        k.prev()

    if args.repeat:
        k.repeat()

    if args.shuffle:
        k.shuffle()

    if args.search:
        k.set_verbosity(1)
        k.search_local_db(args.search)

    if args.rate:
        k.rate(int(args.rate))
            
    if args.audio1:
        k.audio_profile(1)

    if args.audio2:
        k.audio_profile(2)

    if args.audio3:
        k.audio_profile(3)

    if args.audio is "hdmi":
        k.audio_profile(1)

    if args.audio is "3.5":
        k.audio_profile(2)

    if args.audio is "both":
        k.audio_profile(3)

    if args.scanAudio:
        k.scan_audioLibrary()

    if args.scanVideo:
        k.scan_videoLibrary()

    if args.trakt:
        k.addonTrakt()

    if args.delete:
        k.deletNowPlaying()

    if args.fullScreen:
        k.full_screen()

    if args.fave:
        k.add_to_favorite()

    # if args.info:
        # k.show_info()
        # k.show_playlist()

    if args.playlist:
        k.show_info()
        k.show_playlist(limit=200)
        quit()

    if args.input:
        k.get_input()

    if args.test:
        k.test()

    k.show_info()
    k.show_playlist()

