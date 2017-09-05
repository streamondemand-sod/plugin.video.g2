# -*- coding: utf-8 -*-

#
# Resource media mapping.
#
# This file specifies how to use the images present in the Kodi system provided by the
# resource images addons.
#
# The key of the top level dictionary is the prefix to the theme name
# The dictionary item has the following keys:
#     :addon_id:      Kodi resource image addon id. The empty key is reserved for g2;
#     :media_path:    relative to the addon path, specified as a list of hierarchical
#                     folders that will be joined using the os.path.join. If omitted,
#                     is is assumed to be ['resources', 'media'].
#     :themes:        if set to 'folder' means that each sub-folder of the :media_path:
#                     is a different theme whose name is the sub-folder name itself.
#                     If omitted, the resource is assumed to represent a single theme.
#     :mappings:      a dictionary mapping the g2 icon name (without suffix) to the
#                     resource icon name (with or w/o suffix). If the name is the same,
#                     the entry is not required. This key can be altogether omitted if
#                     all the names are the same.
#

{
    # Entry for the g2 resources/media folder
    '': {
        'themes': 'folder',
    },
    # Entry for the Exodus themes in the script.exodus.artwork addon
    'Exodus': {
        'addon_id': 'script.exodus.artwork',
        'themes': 'folder',
        'mappings': {
            'settings': 'tools.png',
            'cache': 'tools.png',
            'moviesTraktcollection': 'trakt.png',
            'moviesTraktwatchlist': 'trakt.png',
            'moviesTraktrated': 'trakt.png',
            'moviesTraktrecommendations': 'trakt.png',
            'movieUserlists': 'userlists.png',
            'mygenesis': 'userlists.png',
            'moviesAdded': 'latest-movies.png',
            'movieSearch': 'search.png',
            'moviePerson': 'people-search.png',
            'movieYears': 'years.png',
            'movieGenres': 'genres.png',
            'movieCertificates': 'certificates.png',
            'moviesTrending': 'featured.png',
            'moviesPopular': 'most-popular.png',
            'moviesViews': 'most-voted.png',
            'moviesBoxoffice': 'box-office.png',
            'moviesOscars': 'oscar-winners.png',
            'moviesTheaters': 'in-theaters.png',
        },
    },

    # Entry for the Covenant themes in the script.covenant.artwork addon
    'Covenant': {
        'addon_id': 'script.covenant.artwork',
        'themes': 'folder',
        'mappings': {
            'settings': 'tools.png',
            'cache': 'tools.png',
            'moviesTraktcollection': 'trakt.png',
            'moviesTraktwatchlist': 'trakt.png',
            'moviesTraktrated': 'trakt.png',
            'moviesTraktrecommendations': 'trakt.png',
            'movieUserlists': 'userlists.png',
            'mygenesis': 'userlists.png',
            'moviesAdded': 'latest-movies.png',
            'movieSearch': 'search.png',
            'moviePerson': 'people-search.png',
            'movieYears': 'years.png',
            'movieGenres': 'genres.png',
            'movieCertificates': 'certificates.png',
            'moviesTrending': 'featured.png',
            'moviesPopular': 'most-popular.png',
            'moviesViews': 'most-voted.png',
            'moviesBoxoffice': 'box-office.png',
            'moviesOscars': 'oscar-winners.png',
            'moviesTheaters': 'in-theaters.png',
        },
    },
}
