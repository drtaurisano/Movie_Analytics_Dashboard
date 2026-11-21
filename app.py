
import streamlit as st
import certifi
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Movie Analytics Dashboard",
    page_icon="🎬",
    layout="wide"
)

# ==================================================
# HEADER
# ==================================================

st.title("🎬 Movie Analytics Dashboard")

st.markdown(
    """
    ### Exploring Movie Trends, Ratings, and Audience Engagement

    This dashboard analyzes movie data stored in **Azure MongoDB**.
    Use the interactive filters to explore movie production trends,
    genre distributions, IMDb ratings, and audience engagement.
    """
)

st.divider()

# ==================================================
# CONNECT TO AZURE MONGODB
# ==================================================

@st.cache_data(ttl=600)
def load_movies():

    connection_string = st.secrets["mongodb"]["connection_string"]

    client = MongoClient(
        connection_string,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=15000
    )

    client.admin.command("ping")

    db = client["movie_analytics"]
    collection = db["movies"]

    movie_data = list(collection.find({}, {"_id": 0}))

    return pd.DataFrame(movie_data)


try:

    # Load data from Azure
    df = load_movies()

    st.success("Connected to Azure MongoDB")

    # ==================================================
    # DATA CLEANING
    # ==================================================

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
    df["imdb_rating"] = pd.to_numeric(df["imdb_rating"], errors="coerce")
    df["imdb_votes"] = pd.to_numeric(df["imdb_votes"], errors="coerce")
    df["num_mflix_comments"] = pd.to_numeric(
        df["num_mflix_comments"], errors="coerce"
    )

    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    # ==================================================
    # SIDEBAR FILTERS
    # ==================================================

    st.sidebar.title("Dashboard Controls")

    st.sidebar.markdown(
        "Use these filters to customize the movies included "
        "in the analysis."
    )

    # Year Filter
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())

    selected_years = st.sidebar.slider(
        "Release Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # Genre Filter
    all_genres = sorted(
        set(
            genre
            for genre_list in df["genres"].dropna()
            if isinstance(genre_list, list)
            for genre in genre_list
        )
    )

    selected_genres = st.sidebar.multiselect(
        "Movie Genres",
        options=all_genres,
        default=[]
    )

    st.sidebar.divider()

    st.sidebar.caption(
        "Leaving genres unselected displays all genres."
    )

    # ==================================================
    # APPLY FILTERS
    # ==================================================

    df_filtered = df[
        (df["year"] >= selected_years[0]) &
        (df["year"] <= selected_years[1])
    ].copy()

    if selected_genres:

        df_filtered = df_filtered[
            df_filtered["genres"].apply(
                lambda genres: any(
                    genre in genres for genre in selected_genres
                ) if isinstance(genres, list) else False
            )
        ]

    # ==================================================
    # KEY STATISTICS
    # ==================================================

    st.header("📊 Key Statistics")

    st.caption(
        "Summary statistics for the movies matching your selected filters."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Movies Analyzed",
        f"{len(df_filtered):,}"
    )

    col2.metric(
        "Average IMDb Rating",
        f"{df_filtered['imdb_rating'].mean():.2f}"
        if not df_filtered["imdb_rating"].dropna().empty
        else "N/A"
    )

    col3.metric(
        "Average Runtime",
        f"{df_filtered['runtime'].mean():.1f} min"
        if not df_filtered["runtime"].dropna().empty
        else "N/A"
    )

    col4.metric(
        "Average IMDb Votes",
        f"{df_filtered['imdb_votes'].mean():,.0f}"
        if not df_filtered["imdb_votes"].dropna().empty
        else "N/A"
    )

    st.divider()

    # ==================================================
    # MOVIE PRODUCTION TRENDS
    # ==================================================

    st.header("📈 Movie Production Trends")

    st.markdown(
        "Examine how the number of movies in the dataset "
        "changes across release years."
    )

    movies_by_year = (
        df_filtered.groupby("year")
        .size()
        .reset_index(name="Number of Movies")
    )

    if not movies_by_year.empty:

        fig_year = px.line(
            movies_by_year,
            x="year",
            y="Number of Movies",
            markers=True,
            title="Movie Releases by Year"
        )

        fig_year.update_layout(
            xaxis_title="Release Year",
            yaxis_title="Number of Movies",
            template="plotly_white",
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_year,
            use_container_width=True
        )

    else:

        st.info("No movies found for the selected filters.")

    st.divider()

    # ==================================================
    # MOVIE RATINGS
    # ==================================================

    st.header("⭐ Movie Ratings")

    st.markdown(
        "Explore the distribution of movie ratings and "
        "how average ratings change over time."
    )

    col1, col2 = st.columns(2)

    with col1:

        rating_data = df_filtered.dropna(
            subset=["imdb_rating"]
        )

        if not rating_data.empty:

            fig_rating = px.histogram(
                rating_data,
                x="imdb_rating",
                nbins=20,
                title="Distribution of IMDb Ratings"
            )

            fig_rating.update_layout(
                xaxis_title="IMDb Rating",
                yaxis_title="Number of Movies",
                template="plotly_white"
            )

            st.plotly_chart(
                fig_rating,
                use_container_width=True
            )

        else:

            st.info("No rating data available.")

    with col2:

        ratings_by_year = (
            df_filtered.groupby("year")["imdb_rating"]
            .mean()
            .reset_index()
        )

        ratings_by_year = ratings_by_year.dropna(
            subset=["imdb_rating"]
        )

        if not ratings_by_year.empty:

            fig_avg_rating = px.line(
                ratings_by_year,
                x="year",
                y="imdb_rating",
                markers=True,
                title="Average IMDb Rating by Year"
            )

            fig_avg_rating.update_layout(
                xaxis_title="Release Year",
                yaxis_title="Average IMDb Rating",
                template="plotly_white"
            )

            st.plotly_chart(
                fig_avg_rating,
                use_container_width=True
            )

        else:

            st.info("No rating data available.")

    st.divider()

    # ==================================================
    # GENRE ANALYSIS
    # ==================================================

    st.header("🎭 Genre Analysis")

    st.markdown(
        "Compare the representation of different genres "
        "within the selected movie collection."
    )

    genre_data = df_filtered.explode("genres")

    genre_counts = (
        genre_data.dropna(subset=["genres"])
        .groupby("genres")
        .size()
        .reset_index(name="Number of Movies")
        .sort_values(
            "Number of Movies",
            ascending=False
        )
    )

    if not genre_counts.empty:

        fig_genres = px.bar(
            genre_counts,
            x="Number of Movies",
            y="genres",
            orientation="h",
            title="Movie Distribution by Genre"
        )

        fig_genres.update_layout(
            yaxis_title="Genre",
            xaxis_title="Number of Movies",
            template="plotly_white",
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            fig_genres,
            use_container_width=True
        )

    else:

        st.info("No genre data available.")

    st.divider()

    # ==================================================
    # AUDIENCE ENGAGEMENT
    # ==================================================

    st.header("👥 Audience Engagement")

    st.markdown(
        "Investigate the relationship between IMDb ratings "
        "and the number of audience votes."
    )

    engagement_data = df_filtered.dropna(
        subset=["imdb_votes", "imdb_rating"]
    )

    if not engagement_data.empty:

        fig_engagement = px.scatter(
            engagement_data,
            x="imdb_votes",
            y="imdb_rating",
            hover_data=["title", "year"],
            title="IMDb Ratings Compared with Audience Votes"
        )

        fig_engagement.update_layout(
            xaxis_title="Number of IMDb Votes",
            yaxis_title="IMDb Rating",
            template="plotly_white"
        )

        st.plotly_chart(
            fig_engagement,
            use_container_width=True
        )

    else:

        st.info("No audience engagement data available.")

    st.divider()

    # ==================================================
    # TOP-RATED MOVIES
    # ==================================================

    st.header("🏆 Top-Rated Movies")

    st.markdown(
        """
        Identify highly rated movies while applying a minimum
        audience vote threshold. This helps reduce the influence
        of movies with very few ratings.
        """
    )

    minimum_votes = st.number_input(
        "Minimum IMDb Votes",
        min_value=0,
        max_value=int(df["imdb_votes"].max()),
        value=1000,
        step=500
    )

    top_movies = df_filtered.dropna(
        subset=["imdb_rating", "imdb_votes"]
    ).copy()

    top_movies = top_movies[
        top_movies["imdb_votes"] >= minimum_votes
    ]

    top_movies = top_movies.sort_values(
        ["imdb_rating", "imdb_votes"],
        ascending=[False, False]
    ).head(20)

    if not top_movies.empty:

        st.caption(
            f"Showing the top {len(top_movies)} movies "
            f"with at least {minimum_votes:,} IMDb votes."
        )

        st.dataframe(
            top_movies[
                [
                    "title",
                    "year",
                    "genres",
                    "imdb_rating",
                    "imdb_votes"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No movies meet the selected vote threshold "
            "and dashboard filters."
        )

    st.divider()

    # ==================================================
    # MOVIE DATA EXPLORER
    # ==================================================

    st.header("🔎 Movie Data Explorer")

    st.markdown(
        "Search and explore individual movies included "
        "in the filtered dataset."
    )

    search_title = st.text_input(
        "Search movie titles",
        placeholder="Enter a movie title..."
    )

    movie_table = df_filtered.copy()

    if search_title:

        movie_table = movie_table[
            movie_table["title"].str.contains(
                search_title,
                case=False,
                na=False
            )
        ]

    movie_table = movie_table.sort_values(
        "imdb_rating",
        ascending=False,
        na_position="last"
    )

    st.dataframe(
        movie_table[
            [
                "title",
                "year",
                "genres",
                "runtime",
                "imdb_rating",
                "imdb_votes"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ==================================================
    # FOOTER
    # ==================================================

    st.divider()

    st.caption(
        f"Movies displayed: {len(df_filtered):,} | "
        f"Database: Azure MongoDB | "
        f"Year range: {selected_years[0]}–{selected_years[1]}"
    )

except Exception as e:

    st.error("Connection to Azure failed.")
    st.exception(e)
