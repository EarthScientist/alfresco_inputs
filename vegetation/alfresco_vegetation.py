# # # # 
# reclassify input NALCMS LandCover Map to classes useful in the ALRESCO Fire Model
#  using pre-processed ancillary layers.
# # # #

# NOTES:  
# a little neighborhood math for the queens case
# ul = (-1,-1)
# uc = (-1, 0)
# ur = (-1,+1)
# l = (0,-1)
# r = (0,+1)
# ll = (+1,-1)
# lc = (+1,0)
# lr = (+1,+1)

def reclassify( rasterio_rst, reclass_list, output_filename, band=1, creation_options=dict() ):
	'''
	MODIFIED: removed window walking...  too slow..

	this function will take a raster image as input and
	reclassify its values given in the reclass_list.
	The reclass list is a simple list of lists with the 
	following formatting:
		[[begin_range, end_range, new_value]]
		ie. [ [ 1,3,5 ],[ 3,4,6 ] ]
			* which converts values 1 to 2.99999999 to 5
				and values 3 to 3.99999999 to 6
				all other values stay the same.
	arguments:
		rasterio_rst = raster image instance from rasterio package
		reclass_list = list of reclassification values * see explanation
		band = integer marking which band you wnat to return from the raster
				default is 1.
		creation_options = gdal style creation options, but in the rasterio implementation
			* options must be in a dict where the key is the name of the gdal -co and the 
			  value is the value passed to that flag.  
			  i.e. 
			  	["COMPRESS=LZW"] becomes dict([('compress','lzw')])
	'''
	# this will update the metadata if a creation_options dict is passed as an arg.
	meta = rasterio_rst.meta
	if len( creation_options ) < 0:
		meta.update( creation_options )

	with rasterio.open( output_filename, mode='w', **meta ) as out_rst:
		band_arr = rasterio_rst.read_band( band )
		band_arr.fill_value = 255 # this is a gotcha
		band_arr = band_arr.data # this is a gotcha
		for rcl in reclass_list:
			band_arr[ np.logical_and( band_arr >= rcl[0], band_arr < rcl[1] ) ] = rcl[2]
		out_rst.write_band( band, band_arr )
	return rasterio.open( output_filename )

if __name__ == '__main__':
	import rasterio, fiona, os, sys
	import numpy as np

	# this should be something passed in at the command line
	gs_value = 6.5
	input_dir = '/workspace/Shared/Tech_Projects/ALFRESCO_Inputs/project_data/Vegetation/Input_Data/alaska_canada'
	output_dir = '/workspace/Shared/Tech_Projects/ALFRESCO_Inputs/project_data/Vegetation/Output_Data'
	
	output_veg = os.path.join( output_dir, 'alfresco_model_vegetation_input_2005.tif' )
	meta_updater = dict( driver='GTiff', dtype=rasterio.uint8, compress='lzw', crs={'init':'epsg:3338'}, count=1, nodata=255 )

	input_paths = {
		'lc05':os.path.join( input_dir, 'na_landcover_2005_1km.tif' ),
		'north_south':os.path.join( input_dir, 'alfresco_north_south_flat.tif' ),
		'mask':os.path.join( input_dir, 'alfresco_vegetation_mask.tif' ),
		'gs_temp':os.path.join( input_dir, 'alfresco_tas_growingseason_1961_1990.tif' ),
		'coast_spruce_bog':os.path.join( input_dir, 'alfresco_coastal_interior_domains.tif' ),
		'treeline':os.path.join( input_dir, 'alfresco_treeline_cavm_derived.tif' ),
		'NoPac':os.path.join( input_dir, 'alfresco_temperate_rainforest_domain.tif' )
	}

	# collapse classes in the input landcover raster
	lc = rasterio.open( input_paths[ 'lc05' ] )
	reclass_list = [[15,16,0],[17,20,0],[128,129,0],[1,3,9],[5,7,3],[11,12,4]]
	output_filename = os.path.join( output_dir, 'alfresco_vegetation_step1.tif' )
	lc_mod = reclassify( lc, reclass_list, output_filename, band=1, creation_options={'init':'epsg:3338'} )
	lc_mod = lc_mod.read_band( 1 )
	lc_mod.fill_value = 9999

	# convert wetland to spruce bog and wetland
	coast_spruce_bog = rasterio.open( input_paths[ 'coast_spruce_bog' ] ).read_band( 1 )
	lc_mod[ (lc_mod == 14) & (coast_spruce_bog == 2) ] = 9
	lc_mod[ (lc_mod == 14) & (coast_spruce_bog != 2) ] = 20

	# coastal wetland class to WETLAND TUNDRA or NO VEG based on the gs_temp (Average Growing Season Temperature) values
	treeline = rasterio.open( input_paths[ 'treeline' ] ).read_band( 1 )
	gs_temp = rasterio.open( input_paths[ 'gs_temp' ] ).read_band( 1 )
	# lc_mod[ (lc_mod == 20) & (gs_temp < gs_value) & (treeline == 1) ] = 9
	# lc_mod[ (lc_mod == 20) ] = 6 # [TEM] keep this for tem
	# lc_mod[ (lc_mod == 20) ] = 0

	lc_mod[ (lc_mod == 20) ] = 6 # test to turn all wetland no spruce bog to wetland tundra

	# turn the placeholder class 8 (Temperate or sub-polar shrubland) into DECIDUOUS or SHRUB TUNDRA
	# NOTE: may be best to do the treeline query here for these weird values <- (treeline == 1) etc
	lc_mod[ (lc_mod == 8) & (gs_temp < gs_value) ] = 4
	lc_mod[ (lc_mod == 8) & (gs_temp >= gs_value) ] = 3

	# Reclass Sub-polar or polar grassland-lichen-moss as GRAMMINOID TUNDRA
	lc_mod[ (lc_mod == 10) | (lc_mod == 12) ] = 5

	# Take the SPRUCE placeholder class and parse it out in to WHITE / BLACK.
	# White Spruce = SPRUCE class & on a South-ish Facing slope
	north_south = rasterio.open( input_paths[ 'north_south' ] ).read_band( 1 )
	lc_mod[ (lc_mod == 9) & (north_south == 1) ] = 2
	lc_mod[ (lc_mod == 9) & (north_south == 2) ] = 1
	lc_mod[ (lc_mod == 9) ] = 1 # convert low lying spruce leftover to black spruce

	# [TEM] convert Barren to Heath
	lc_mod[ (lc_mod == 16) ] = 9

	# reclassify erroneous spruce pixels with the most common values of its neighbors
	# lc_mod = replace_erroneous_treeline( lc_mod, treeline )
	lc_mod[ ((lc_mod == 1) | (lc_mod == 2)) & (treeline == 1) ] = 5 # just convert it to gramminoid tundra which is the whole area...

	# temperate rainforest (seak) region delineation
	temperate_rainforest = rasterio.open( input_paths[ 'NoPac' ] ).read_band( 1 )
	lc_mod[ (lc_mod > 0) & (temperate_rainforest == 1) ] = 8

	# conversion of the barren-lichen moss
	lc_mod[ lc_mod == 13 ] = 7

	# convert oob to 255
	lc_mod.fill_value = 255

	# change the type ( byte ) and write it out
	meta = lc.meta.copy()
	meta.update( meta_updater )

	with rasterio.open( output_veg, 'w', **meta ) as out:
		out.write_band( 1, lc_mod.astype( rasterio.uint8 ) )

