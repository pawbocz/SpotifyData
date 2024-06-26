import streamlit as st
import plotly.express as px
import pandas as pd
from lyricsgenius import Genius
import requests

Genius_API = st.secrets['GENIUS_API']

st.set_page_config(page_title='SpotifyData', page_icon='🎵', layout="wide")

#apply style.css CSS
with open("style.css" ) as css:
    st.markdown( f'<style>{css.read()}</style>' , unsafe_allow_html= True)

@st.cache_data
def load_data(dane):
    return pd.read_json(dane)

def donut(dane:pd.DataFrame | pd.Series,values,names,title:str,middle_text:str,hole=0.5,**annotations):
    ponczek = px.pie(dane,values=values,names=names,hole=hole,title=title)
    if annotations is not None:
        ponczek.update_layout(annotations=[dict(text=middle_text,x=0.50,y=0.5,font_size=18,showarrow=False)],font=dict(color='black'))
    else:
        ponczek.update_layout(annotations=[annotations],font=dict(color='black'))
    return ponczek

def format_minutes(minutes):
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes - hours * 60 - mins) * 60)
    return f"{hours}:{mins}:{secs}"

@st.cache_data
def getLyricsTop3(artist: str, *songs):
    genius = Genius(Genius_API)
    genius.search_song()
    artist_object = genius.search_artist(artist, max_songs=3,)
    
    lyrics_dict = {}
    for song in artist_object.songs:
        title = song.title
        lyrics = song.lyrics
        lyrics_dict[title] = lyrics
    
    return lyrics_dict

@st.cache_data
def getAlbumInfo(artist:str,album:str):
    genius = Genius(Genius_API)
    albumResponse = genius.search_album(album,artist).to_dict()
    
    cleanDict = {'albumInfo':[{
                               'author':albumResponse['artist']['name'],
                               'authorID':albumResponse['artist']['id'],
                               'albumName':albumResponse['name'],
                               'albumID':albumResponse['id'],
                               'coverArt':albumResponse['cover_art_thumbnail_url']
                               }]}
    tracks = {}
    for track in albumResponse['tracks']:
        cleanedLyrics = track['song']['lyrics'].replace('\n', ' ')
        cleanedTitle = track['song']['title'].replace('\u200b', '')

        tracks[cleanedTitle] = [{
                                'trackCoverArt':track['song']['song_art_image_thumbnail_url'],
                                "id":track['song']['id'],
                                "lyrics":cleanedLyrics}]
        
    cleanDict['tracks'] = tracks

    return cleanDict
    

def main():

    with st.sidebar:

        dane = st.file_uploader(label='Prześlij plik',type={"csv", "txt","json"})
        moje_example = st.sidebar.checkbox("Wczytaj dane przykładowe (💀)")
        if moje_example:
            dane = 'Data\MyAwfulMusicTaste.json'

        st.info('Obsługiwany plik to (StreamingHistory_music_0.json),jest to historia odtwarzania Spotify, którą możesz pobrać [tutaj](https://www.spotify.com/us/account/privacy/)',icon='🤓')

    if dane is not None:
        
        dane = load_data(dane)

        with st.sidebar:
            st.markdown(f"Struktura tabeli:")
            st.markdown(f"**{dane.shape[1]}** - kolumny")
            st.markdown(f"**{dane.shape[0]}** - wiersze")



        chosen_artist = st.sidebar.multiselect("Artyści których słuchałeś: ",options=dane.artistName.unique(),placeholder="Wybierz artystę")
        st.sidebar.multiselect(label="Ich piosenki: ",options=dane['trackName'].loc[dane['artistName'].isin(chosen_artist)].unique(),placeholder="Wybierz utwór")
        
        track_play_time = (dane.groupby(['trackName','artistName'])['msPlayed']
                                .sum(numeric_only=True)
                                .sort_values(ascending=False)
                                .reset_index()) 
            
        artist_play_time = (dane.groupby('artistName')['msPlayed']
                                .sum()
                                .sort_values(ascending=False)
                                .reset_index())
        
        #Zmiana kolumny msPlayed na minPlayed i formatowanie msPlayed do %H%M%S w kolumnie HrMinSec
        track_play_time['msPlayed'] = round(track_play_time['msPlayed']/60000,2)
        track_play_time.columns = ['trackName','artistName','minPlayed']
        track_play_time['HrMinSec'] = pd.to_datetime((track_play_time['minPlayed'].apply(format_minutes)),format='%H:%M:%S').dt.time
        
        artist_play_time['msPlayed'] = round(artist_play_time['msPlayed']/60000,2)
        artist_play_time.columns = ['artistName','minPlayed']
        artist_play_time['HrMinSec'] = pd.to_datetime((artist_play_time['minPlayed'].apply(format_minutes)),format='%H:%M:%S').dt.time


        #Sunburst chart filtering
        artists_to_exclude = track_play_time.groupby('artistName')['minPlayed'].sum()
        artists_to_exclude = artists_to_exclude[artists_to_exclude <=60].index

        sunData = track_play_time[~track_play_time['artistName'].isin(artists_to_exclude)]
            
        sunBurst = px.sunburst(sunData, 
                  path=['artistName', 'trackName'], 
                  values='minPlayed', 
                  title="Rozbłysk słońca (sunburst) wykres artystów i ich piosenek")

        sunCheck = st.checkbox("Sunburst chart, mega cool ale potencjalnie zamuli strone 🤓☝️")
        
        if sunCheck:
            st.plotly_chart(sunBurst)

        if st.checkbox("Staty Top 5",value=True):
            col1,col2 = st.columns(2)
            
            top_5_tracks = track_play_time.head(5)
            others_tracks = pd.DataFrame([{
                'trackName':'Others',
                'artistName':'Others',
                'minPlayed':track_play_time['minPlayed'][5:].sum(),
                'HrMinSec':format_minutes(track_play_time['minPlayed'][5:].sum())
                }])
            
            top_5_tracks_others = pd.concat([top_5_tracks,others_tracks])
            
            top_5_artists = artist_play_time.head(5)
            others_artists = pd.DataFrame([{
                'artistName':'Others',
                'minPlayed':artist_play_time['minPlayed'][5:].sum(),
                'HrMinSec':format_minutes(artist_play_time['minPlayed'][5:].sum())
                }])
            
            top_5_artist_others = pd.concat([top_5_artists,others_artists])
            
            dfcol1,dfcol3 = st.columns(2,gap="small")
            with dfcol1:
                st.markdown("**Wszyscy Artyści których słuchasz**")
                st.dataframe(artist_play_time,hide_index=True)
            
            with dfcol3:
                st.markdown("**Wszystkie piosenki których słuchałeś**")
                st.dataframe(track_play_time,hide_index=True)
            
            #Tworzenie kolumn i wstawianie 2 grafów 
            artcol1,artcol2 = st.columns(2)

            with artcol1:
                st.plotly_chart(donut(top_5_artist_others,values='minPlayed',names='artistName',title="Top 5 artystów",middle_text='Top 5 procentowo'))
            with artcol2:
                st.plotly_chart(px.bar(artist_play_time.head(),x='artistName',y='minPlayed',color='minPlayed'))

            songcol1,songcol2 = st.columns(2)

            with songcol1:
                st.plotly_chart(donut(top_5_tracks,values='minPlayed',names='trackName',title="Top 5 tracków",middle_text='Top 5 procentowo'),use_container_width=True)
            with songcol2:
                st.plotly_chart(px.bar(track_play_time.head(),x='trackName',y='minPlayed',color='minPlayed'),use_container_width=True)


if __name__ == "__main__":
    main()


