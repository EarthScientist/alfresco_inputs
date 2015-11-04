# script to bring the GIRR Radiation at top of Atmosphere through the clouds to generate 
# a sort of rsds dataset for TEM Model in the IEM Project
def generate_rsds( girr_month_fn, cld_month_fn_list ):
	girr = rasterio.open( girr_month_fn )
	girr_arr = girr.read( 1 )

	def f( cld_fn, girr_arr ):
		cld = rasterio.open( cld )
		cld_arr = cld.read( 1 )
		rsds_arr = girr_arr * cld_arr

		meta = cld.meta
		meta.update( compress=lzw )
		if 'transform' in meta.keys():
			meta.pop( 'transform' )

		with rasterio.open( output_filename, 'w', **meta ) as out:
			out.write( rsds_arr, 1 )
		return output_filename

	_ = [ f( cld, girr_arr ) for cld in cld_month_fn_list ]
	return 1


if __name__ == '__main__':
	import os, glob, rasterio
	import numpy as np
	import pandas as pd

	# list the girr
	girr_dir = '/workspace/Shared/Tech_Projects/ALFRESCO_Inputs/project_data/TEM_Data/girr_radiation_cmip3_process'
	girr = sorted( glob.glob( os.path.join( girr_dir, '*.tif' ) ) )

	# list the cloud files for a series
	cld_dir = '/workspace/Shared/Tech_Projects/ALFRESCO_Inputs/project_data/TEM_Data/cru_october_final/cru_ts31/cld/downscaled'
	cld = sorted( glob.glob( os.path.join( cld_dir, '*.tif' ) ) )

	# return the month from each cld filename and groupby that
	cld = pd.Series( cld )
	cld_month_groups = cld.groupby( cld.apply( lambda x: os.path.basename( x ).split( '.' )[0].split( '_' )[-2] ) )



	# # # OLD R CODE THAT WE USED FROM DAVE MC GUIRE
	# now we calculate the nirr from the girr and the cloudcover percent using the code from Dave McGuire
	##############################################################################################################
	#		** this is the c++ version given by Dave.  I am using R to calculate it here
	#		if (clds > -0.1) {
	#			nirr = cld.subset.v * (0.251 + (0.509*(1.0 - clds/100.0))) # basically percent cloudcover
	#			}else { 
	#				nirr = -999.9; }
	##############################################################################################################

	output.v <- getValues(downscaled.interp.r)
	
	#ind <- which(values(downscaled.interp.r) > -0.1)
	oob <- which(values(downscaled.interp.r) <= -0.1)
	
	if(length(oob)>0){
		nirr = rad.monthly.current * (0.251 + (0.509 * (1.0 - downscaled.interp.r/100)))
		values(nirr)[oob] <- -9999
	}else{
		nirr = rad.monthly.current * (0.251 + (0.509 * (1.0 - downscaled.interp.r/100)))
	}


