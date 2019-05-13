# Update ArcGIS Online Layers

These scripts are used to automate the updating of 
ArcGIS Online operational layers used in our organization,
particularly to ensure that web maps and ArcGIS Collector
applications have the most current data available in our 
corporate databases. 

## Modules
---

### **update_vector_tile_layers**

Using and existing ArcGIS Pro project that contains a map, and a premade
empty feature class in the web Mercator projection (WKID 3857), this module
will:

1. Remove all existing layer files from the map.
2. Add a blank layer to the map that is in the web Mercator
   projection (WKID 3857). This is necessary so that the map is in
   the right projection for packaging in the Arcgis/google/Bing maps
   tiling scheme
3. Add the layers specified in the vector_layers dictionary to the map.
   The keys represent the name of the vector tile package(vtpk).
   The values are a list of the layers to include in the vtpk.
4. Creates the vtpk locally, overwriting any existing vtpk.
5. Checks AGOL for existing tile packages and hosted tile layers
   and deletes them. Overwriting tile packages/layers is not
   supported at this time (April 2019).
6. Add the vtpk to AGOL, publishes it as a hosted tile layer
   and shares it with the organization and the AGOL group.
7. Removes the layers from the map.

