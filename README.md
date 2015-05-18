Swag AP analysis tool by Jake and Max and Mitar (great sage)

install requirements from requirements.txt:

    pip install -r requirements.txt

The goal of the project is to create a network topology of the Cloyne Court Wifi deployment to identify optimal access point channel assignments and rogue nodes within the house. 

Channel Assignment Project: (Max)
============

Goal: Avoid having APs near each other (that can pick up each other's signals) on the same channel. 

Method:

Access the feed of each AP listed on Cloyne Github, pull down json feed and parse to create a network graph. 

Run graph three coloring, removing the weakest connection, until there are no access points with edges that have the same coloring. (an optimal channel assignment will then be achieved)

Rogue Node Project: (Jake)
=============

Goal: Hunt down and destroy non-cooperative, non-Cloyne personal access points within the house. 


