"""Update vector tile packages and associated vector tile layers in
Arcgis Online (AGOL).

Using an existing ArcGIS Pro project (aprx) with an existing empty
map this script will:

1. Remove all existing layer files from the map.
2. Add a blank layer to the map that is in the web mercator
   projection (WKID 3857). This is nessecary so that the map is in
   the right projection for packaging in the Arcgis/google/bing maps
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

"""

import os
import arcgis
import arcpy
import utilities

# CONSTANTS
ROOT_DIRECTORY = r'D:\jhth490\projects\mobile_suma'
# Arcgis Online login credentials stored as environmental variables
# so that they are not exposed in the code.
USERNAME = os.environ.get('AGOL_USERNAME')
PASSWORD = os.environ.get('AGOL_PASSWORD')
# Path to the ArcGIS Pro Project
APRX_PATH = (
    r'D:\jhth490\projects\mobile_suma'
    r'\mobile_suma_gis\mobile_suma_gis.aprx'
)
# Name of the map to add the layers to. It could be helpful to only
# have one map in the project
MAP = 'collector_map'
# Path to the highest level folder that holds the layers to use.
QDL_PATH = r'\\dnr\agency\app_data_gis\qdl\core'
AGOL = 'https://www.arcgis.com'
# AGOL username of the owner of the items
OWNER = 'jhth490'
# ID of the AGOL group to share the vtpks and tile layers. This helps
# with searching and deleting items and managing shared content.
GROUP_ID = '4154c84c38204236a0a633665f040976'
LOGGER = utilities.setup_logging(ROOT_DIRECTORY)
# Pre-created blank feature class in web mercator projection (WKID 3857).
SPATIAL_REFERENCE_LAYER = (r"D:\jhth490\projects\mobile_suma\mobile_suma_gis"
                           r"\mobile_suma_gis.gdb\fc_set_spatial_reference")
# Dictionary containing the layers to add to the map. These are relative
# to the QDL_PATH above. Keys are the name of vtpk, values are paths to
# the layer files to include in the vtpk.
VECTOR_LAYERS = {
    'Transportation': [
        r'Transportation\State Lands - Active Roads Group',
        r'Transportation\State Lands - Road Barriers'
    ],
    'Topography': [
        r'Topography\Contours 40, 200, 1000, 2000-foot (USGS DEM 10-meter)'
    ],
    'State Lands Knowledge': [
        (r'Forest Management\State Lands Knowledge'
         r'\1 All State Lands Knowledge by category'),
    ],
}


def remove_all_layers(m):
    """Accepts a map object created with the arcpy.mp module
    and removes all of the layers currently in the map """

    # Delete group layers first so we don't get a runtime error
    group_layers_to_remove = m.listLayers()
    for layer in group_layers_to_remove:
        if layer.isGroupLayer:
            LOGGER.info(f'removing group layer: {layer}')
            m.removeLayer(layer)
    # Now delete non-group layers
    layers_to_remove = m.listLayers()
    LOGGER.debug(layers_to_remove)
    for layer in layers_to_remove:
        LOGGER.info(f'removing layer: {layer}')
        m.removeLayer(layer)


def turn_on_layers_in_map(m):
    """Make sure all the layers in the map are turned on so
    that they will show up in the tile layers."""

    layers = m.listLayers()
    for layer in layers:
        layer.visible = True


@utilities.timer(LOGGER)
def add_vector_tile_layers(vector_layers):
    """ Accepts the dictionary of vector layers, adds them to a map,
    creates the vector tile package locally, deletes the exisiting layer
    in AGOL if it exists, uploads the tile package to AGOL and then
    publishes the tile package to a hosted tile layer
    """

    aprx = arcpy.mp.ArcGISProject(APRX_PATH)
    m = aprx.listMaps(MAP)[0]
    gis = arcgis.GIS(AGOL, USERNAME, PASSWORD)

    remove_all_layers(m)
    # Get the group object for the mobile suma AGOL group
    mobile_suma_group = gis.groups.get(GROUP_ID)
    LOGGER.debug(f'Group name: {mobile_suma_group.title} found')
    for k, v in vector_layers.items():
        # First add a dummy layer to the map so that it sets the spatial
        # reference of the map to Web Mercator. This is nessecary to
        # publish to the AGOL/Google maps tiling scheme.
        LOGGER.info(f'creating spatial reference layer for {k} group')
        arcpy.MakeFeatureLayer_management(
            SPATIAL_REFERENCE_LAYER,
            'spatial_reference_layer')
        m.addDataFromPath(SPATIAL_REFERENCE_LAYER)
        LOGGER.info(f'added spatial reference layer for {k}')
        for i in v:
            layer = arcpy.mp.LayerFile(os.path.join(QDL_PATH, i + ".lyr"))
            LOGGER.info(f'adding layer: {layer} to map')
            m.addLayer(layer)
        # Make sure all the layers are on
        turn_on_layers_in_map(m)
        # Create the vector tile package locally
        LOGGER.info('Creating Vector tile package locally')
        arcpy.CreateVectorTilePackage_management(
            m,
            f'mobile_suma_gis/vector_tile_packages/{k}.vtpk',
            'ONLINE',
            )
        LOGGER.info(f'finished creating vtpk')
        # Delete the old package and tile layer. The name of the old layer and
        # new layer must match or they will break links from web maps.
        # AGOL does not currently support overwriting tile
        # packages, only feature services
        LOGGER.info('Checkinig if content already exists on AGOL and'
                    'deleting if it does.')

        agol_items = gis.content.search(
            f'owner:{OWNER} AND title:{k} AND group:{GROUP_ID}'
        )
        if len(agol_items) > 0:
            for agol_item in agol_items:
                LOGGER.info(f'Deleting {agol_item}')
                agol_item.delete()
        else:
            LOGGER.info('No items to delete from agol.')
        # Publish to AGOL.
        LOGGER.info('Adding vtpk to AGOL')
        vtpk = gis.content.add(
            {'description': (f'VTPK for the {k} group'
             'layer this layer is updated weekly.')},
            f'mobile_suma_gis/vector_tile_packages/{k}.vtpk',
            folder='vector_tiles'
        )
        # When using the share method you must use the gis group object.
        # Using the group id or name does not work, despite what the
        # documentation says.
        vtpk.share(org=True, groups=[mobile_suma_group])
        LOGGER.info('Publishing hosted tile layer')
        publish = vtpk.publish()
        publish.share(org=True, groups=[mobile_suma_group])

        # Remove the layers. All active layers in the map
        # will be included in the vtpk
        LOGGER.info('Removing layers from map.')
        remove_all_layers(m)


def main():
    try:
        try:
            utilities.setup_arcpy_environment()
        except:
            LOGGER.debug('Unable to set arcpy environment')
            raise Exception
        try:
            add_vector_tile_layers(VECTOR_LAYERS)
        except:
            LOGGER.debug('Failed to excecute add_vector_tile_layer function')
            raise Exception
        return True
    except Exception as e:
        LOGGER.exception(e)
        # LOGGER.exception(arcpy.GetMessages())
        return False
    finally:
        # Clean up the layers in the map in case the script failed.
        aprx = arcpy.mp.ArcGISProject(APRX_PATH)
        m = aprx.listMaps(MAP)[0]
        remove_all_layers(m)
        del m
        del aprx


if __name__ == '__main__':
    if main():
        LOGGER.warning('script ran successfully')
    else:
        LOGGER.error('Script failed. See log file')
