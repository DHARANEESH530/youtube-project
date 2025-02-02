
from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st

#API KEY CONNECTION

def Api_connect():
    Api_Id="AIzaSyA3q5bk8hDwoLryx6ZvioCPQd1JmA6pWGM"

    api_service_name="youtube"
    api_version="v3"

    youtube=build(api_service_name,api_version,developerKey=Api_Id)

    return youtube

youtube=Api_connect()


#GET CHANNAL INFORMATION
def get_channel_info(channel_id):
    request=youtube.channels().list(
                part="snippet,contentDetails,statistics",
                id=channel_id
    )
    response=request.execute()

    for i in response['items']:
        data=dict(Channel_Name=i["snippet"]["title"],
                 Channel_Id=i["id"],
                 Subscribers=i["statistics"]["subscriberCount"],
                 Views=i["statistics"]["viewCount"],
                  Total_Videos=i["statistics"]["videoCount"],
                  Channel_Description=i["snippet"]["description"],
                  Playlist_Id=i["contentDetails"]["relatedPlaylists"]["uploads"])
    return data   
       
#get video ids
def get_videos_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id,
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=Playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids


#get video information
def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,ContentDetails,statistics",
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                      channel_Id=item['snippet']['channelId'],
                      Video_Id=item['id'],
                      Title=item['snippet']['title'],
                      Tags=item['snippet'].get('tags'),
                      Thumbnail=item['snippet']['thumbnails']['default']['url'],
                      Description=item['snippet'].get('description'),
                      Published_date=item['snippet']['publishedAt'],
                      Duration=item['contentDetails']['duration'],
                      Views=item['statistics'].get('viewCount'),
                      Likes=item['statistics'].get('likeCount'),
                      Comments=item['statistics'].get('commentCount'),
                      Favorite_count=item['statistics']['favoriteCount'],
                      Definition=item['contentDetails']['definition'],
                      Caption_status=item['contentDetails']['caption']
                     )
            video_data.append(data)
    return video_data
       

#get comment information
def get_comment_info(video_Ids):
    comment_data=[]
    try:
        for video_id in video_Ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId= video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(comment_Id=item['snippet']['topLevelComment']['id'],
                          video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                          Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                          Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                          Comment_published=item['snippet']['topLevelComment']['snippet']['publishedAt'])

                comment_data.append(data)

    except:
        pass
    return comment_data


#get_playlist_details

def get_playlist_details(channel_id):
        next_page_token=None
        All_data=[]
        while True:
                request=youtube.playlists().list(
                        part='snippet,contentDetails',
                        channelId=channel_id,
                        maxResults=50,
                        pageToken=next_page_token
                )
                response=request.execute()

                for item in response['items']:
                        data=dict(Playlist_Id=item['id'],
                                  Title=item['snippet']['title'],
                                  Channel_Id=item['snippet']['channelId'],
                                  Channel_Name=item['snippet']['channelTitle'],
                                  PublishedAt=item['snippet']['publishedAt'],
                                  Video_Count=item['contentDetails']['itemCount'])
                        All_data.append(data)

                next_page_token=response.get('nextPageToken')
                if next_page_token is None:
                        break
        return All_data


#UPLOAD TO MONGODB
mongodb_url="mongodb://localhost:27017"
client=pymongo.MongoClient(mongodb_url)
db_name = "Youtube_Data" 
db = client[db_name]


def channel_details(channel_id):
    ch_details=get_channel_info(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)
    com_details=get_comment_info(vi_ids)
    pl_details=get_playlist_details(channel_id)
    
    
    coll1=db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,
                     "viedo_information":vi_details,"comment_information":com_details})
    
    return "upload completed successfully"


#Table creation for channels,playlist,viedos,comments
def channels_table():
    mydb=psycopg2.connect(host="localhost",
                          user="postgres",
                          password=1999,
                          database="Youtubedata",
                          port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query='''create table if not exists channels(Channel_Name varchar(2000),
                                                            Channel_Id varchar(2000) primary key,
                                                            Subscribers bigint,
                                                            Views bigint,
                                                            Total_Videos int,
                                                            Channel_Description text,
                                                            Playlist_Id varchar(1000))'''

        cursor.execute(create_query)
        mydb.commit()
    except:
        print("channels table already created")


    ch_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=pd.DataFrame(ch_list)   




    for index,row in df.iterrows():
        insert_query='''insert into channels(Channel_Name,
                                             Channel_Id,
                                             Subscribers,
                                             Views,
                                             Total_Videos,
                                             Channel_Description,
                                             Playlist_Id)

                                             values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Subscribers'],
                row['Views'],
                row['Total_Videos'],
                row['Channel_Description'],
                row['Playlist_Id'])

        try:
            cursor.execute(insert_query,values)
            mydb.commit()

        except:
            print("channels values are already inserted")


def playlist_table():
    mydb=psycopg2.connect(host="localhost",
                          user="postgres",
                          password=1999,
                          database="Youtubedata",
                          port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists playlists'''
    cursor.execute(drop_query)
    mydb.commit()


    create_query='''create table if not exists playlists(Playlist_Id varchar(2000)primary key,
                                                            Title varchar(2000),
                                                            Channel_Id varchar(2000),
                                                            Channel_Name varchar(2000),
                                                            PublishedAt timestamp,
                                                            Video_Count int)'''



    cursor.execute(create_query)
    mydb.commit()

    
    pl_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=pd.DataFrame(pl_list)
    
    for index,row in df1.iterrows():
        insert_query='''insert into playlists(Playlist_Id,
                                             Title,
                                             Channel_Id,
                                             Channel_Name,
                                             PublishedAt,
                                             Video_Count
                                             )

                                             values(%s,%s,%s,%s,%s,%s)'''
        values=(row['Playlist_Id'],
                row['Title'],
                row['Channel_Id'],
                row['Channel_Name'],
                row['PublishedAt'],
                row['Video_Count'])
                

        
        cursor.execute(insert_query,values)
        mydb.commit()
    

def videos_table():
    mydb=psycopg2.connect(host="localhost",
                          user="postgres",
                          password=1999,
                          database="Youtubedata",
                          port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists videos'''
    cursor.execute(drop_query)
    mydb.commit()


    create_query='''create table if not exists videos(Channel_Name varchar(2000),
                                                      channel_Id varchar(2000),
                                                      Video_Id varchar(2000) primary key,
                                                      Title varchar(5000),
                                                      Tags text,
                                                      Thumbnail varchar(5000),
                                                      Description text,
                                                      Published_date timestamp,
                                                      Duration interval,
                                                      Views bigint,
                                                      Likes bigint,
                                                      Comments int,
                                                      Favorite_count int,
                                                      Definition varchar(1000),
                                                      Caption_status varchar(500)
                                                      )'''



    cursor.execute(create_query)
    mydb.commit()


    vi_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"viedo_information":1}):
        for i in range(len(vi_data["viedo_information"])):
            vi_list.append(vi_data["viedo_information"][i])
    df2=pd.DataFrame(vi_list)


    for index,row in df2.iterrows():
            insert_query='''insert into videos(Channel_Name,
                                                  channel_Id,
                                                  Video_Id,
                                                  Title,
                                                  Tags,
                                                  Thumbnail,
                                                  Description,
                                                  Published_date,
                                                  Duration,
                                                  Views,
                                                  Likes,
                                                  Comments,
                                                  Favorite_count,
                                                  Definition,
                                                  Caption_status
                                                 )

                                                 values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
            values=(row['Channel_Name'],
                    row['channel_Id'],
                    row['Video_Id'],
                    row['Title'],
                    row['Tags'],
                    row['Thumbnail'],
                    row['Description'],
                    row['Published_date'],
                    row['Duration'],
                    row['Views'],
                    row['Likes'],
                    row['Comments'],
                    row['Favorite_count'],
                    row['Definition'],
                    row['Caption_status']
                   )



            cursor.execute(insert_query,values)
            mydb.commit()


def comments_table():
    mydb=psycopg2.connect(host="localhost",
                          user="postgres",
                          password=1999,
                          database="Youtubedata",
                          port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists comments'''
    cursor.execute(drop_query)
    mydb.commit()


    create_query='''create table if not exists comments(comment_Id varchar(10000) primary key,
                                                        video_Id varchar(5000),
                                                        Comment_Text text,
                                                        Comment_Author varchar(1500),
                                                        Comment_published timestamp
                                                        )'''



    cursor.execute(create_query)
    mydb.commit()


    com_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=pd.DataFrame(com_list)


    for index,row in df3.iterrows():
            insert_query='''insert into comments(comment_Id,
                                                 video_Id,
                                                 Comment_Text,
                                                 Comment_Author,
                                                 Comment_published
                                                )

                                                 values(%s,%s,%s,%s,%s)'''
            values=(row['comment_Id'],
                    row['video_Id'],
                    row['Comment_Text'],
                    row['Comment_Author'],
                    row['Comment_published']
                   )



            cursor.execute(insert_query,values)
            mydb.commit()



def tables():
    channels_table()
    playlist_table()
    videos_table()
    comments_table()
    
    return "Tables created successfully"


def show_channels_table():
    ch_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)
    
    return df


def show_playlist_table():
    pl_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=st.dataframe(pl_list)
    
    return df1


def show_videos_table(): 
    vi_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"viedo_information":1}):
        for i in range(len(vi_data["viedo_information"])):
            vi_list.append(vi_data["viedo_information"][i])
    df2=st.dataframe(vi_list)
    
    return df2


def show_comments_table():
    com_list=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3=st.dataframe(com_list)
    
    return df3



#streamlit 

with st.sidebar:
    st.title(":blue[YOUTUBE DATA HARVESTING]")
    st.header("Data is Anywhere and Everywhere")
    st.caption("Python Scripting")
    st.caption("Data Collection")
    st.caption("MongoDB")
    st.caption("API Intergration")
    st.caption("Data Management using MongoDB and SQL")
    
channel_id=st.text_input("Enter the channel ID")    

if st.button("Collect & Store data"):
    ch_ids=[]
    db=client["Youtube_Data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"]["Channel_Id"])
        
    if channel_id in ch_ids:
        st.success("Channel Details of the given channel id already exists")
        
    else:
        insert=channel_details(channel_id)
        st.success(insert)
        
if st.button("Migrate to sql"):
    Table=tables()
    st.success(Table)
    
show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","PLAYLISTS","VIDEOS","COMMENTS"))

if show_table =="CHANNELS":
    show_channels_table()
    
elif show_table =="PLAYLISTS":    
    show_playlist_table() 
    
elif show_table =="VIDEOS":    
    show_videos_table()    

elif show_table =="COMMENTS":    
    show_comments_table()
    

#sql connecti0n

mydb=psycopg2.connect(host="localhost",
                      user="postgres",
                      password=1999,
                      database="Youtubedata",
                      port="5432")
cursor=mydb.cursor()

