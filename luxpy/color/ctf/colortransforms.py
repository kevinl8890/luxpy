# -*- coding: utf-8 -*-
########################################################################
# <LUXPY: a Python package for lighting and color science.>
# Copyright (C) <2017>  <Kevin A.G. Smet> (ksmet1977 at gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#########################################################################
"""
Module with functions related to basic colorimetry
==================================================

Note
----

  Note that colorimetric data is always located in the last axis
  of the data arrays. (See also xyz specification in __doc__ string
  of luxpy.spd_to_xyz())

colortransforms.py
------------------

 :_CSPACE_AXES: dict with list[str,str,str] containing axis labels
                of defined cspaces
 :_IPT_M: Conversion matrix for IPT color space
  
 :_COLORTF_DEFAULT_WHITE_POINT : default white point for colortf (set at Illuminant E)


Supported chromaticity / colorspace functions:
  | * xyz_to_Yxy(), Yxy_to_xyz(): (X,Y,Z) <-> (Y,x,y);
  | * xyz_to_Yuv(), Yuv_to_Yxy(): (X,Y,Z) <-> CIE 1976 (Y,u',v');
  | * xyz_to_xyz(), lms_to_xyz(): (X,Y,Z) <-> (X,Y,Z); for use with colortf()
  | * xyz_to_lms(), lms_to_xyz(): (X,Y,Z) <-> (L,M,S) cone fundamental responses
  | * xyz_to_lab(), lab_to_xyz(): (X,Y,Z) <-> CIE 1976 (L*a*b*)
  | * xyz_to_luv(), luv_to_xyz(): (X,Y,Z) <-> CIE 1976 (L*u*v*)
  | * xyz_to_Vrb_mb(),Vrb_mb_to_xyz(): (X,Y,Z) <-> (V,r,b); [Macleod & Boyton, 1979]
  | * xyz_to_ipt(), ipt_to_xyz(): (X,Y,Z) <-> (I,P,T); (Ebner et al, 1998)
  | * xyz_to_Ydlep(), Ydlep_to_xyz(): (X,Y,Z) <-> (Y,dl, ep); 
  |                   Y, dominant wavelength (dl) and excitation purity (ep)
  | * xyz_to_srgb(), srgb_to_xyz(): (X,Y,Z) <-> sRGB; (IEC:61966 sRGB)
  | * xyz_to_jabz(), jabz_to_xyz(): (X,Y,Z) <-> (Jz,az,bz) (Safdar et al, 2017)

References
----------
    1. `CIE15:2018, “Colorimetry,” CIE, Vienna, Austria, 2018. <https://doi.org/10.25039/TR.015.2018>`_
    2. `Ebner F, and Fairchild MD (1998).
       Development and testing of a color space (IPT) with improved hue uniformity.
       In IS&T 6th Color Imaging Conference, (Scottsdale, Arizona, USA), pp. 8–13.
       <http://www.ingentaconnect.com/content/ist/cic/1998/00001998/00000001/art00003?crawler=true>`_
    3. `MacLeod DI, and Boynton RM (1979).
       Chromaticity diagram showing cone excitation by stimuli of equal luminance.
       J. Opt. Soc. Am. 69, 1183–1186.
       <https://www.osapublishing.org/josa/abstract.cfm?uri=josa-69-8-1183>`_
    4. `Safdar, M., Cui, G., Kim,Y. J., and  Luo,M. R. (2017).
       Perceptually uniform color space for image signals including high dynamic range and wide gamut.
       Opt. Express, vol. 25, no. 13, pp. 15131–15151, Jun. 2017.
       <https://www.opticsexpress.org/abstract.cfm?URI=oe-25-13-15131>`_

.. codeauthor:: Kevin A.G. Smet (ksmet1977 at gmail.com)

Created on Wed Jun 28 22:48:09 2017
"""

from luxpy import _CMF, _CIE_ILLUMINANTS, _CIEOBS, _CSPACE, math, spd_to_xyz 
from luxpy.utils import np, np2d, np2dT, np3d, todim, asplit, ajoin

__all__ = ['_CSPACE_AXES', '_IPT_M','xyz_to_Yxy','Yxy_to_xyz','xyz_to_Yuv','Yuv_to_xyz',
           'xyz_to_wuv','wuv_to_xyz','xyz_to_xyz','xyz_to_lms', 'lms_to_xyz','xyz_to_lab','lab_to_xyz','xyz_to_luv','luv_to_xyz',
           'xyz_to_Vrb_mb','Vrb_mb_to_xyz','xyz_to_ipt','ipt_to_xyz','xyz_to_Ydlep','Ydlep_to_xyz','xyz_to_srgb','srgb_to_xyz',
           'xyz_to_jabz','jabz_to_xyz']

#------------------------------------------------------------------------------
# Database with cspace-axis strings (for plotting):
_CSPACE_AXES = {'Yxy': ['Y / L (cd/m²)', 'x', 'y']}
_CSPACE_AXES['Yuv'] = ['Y / L (cd/m²)', "u'", "v'"]
_CSPACE_AXES['xyz'] = ['X', 'Y', 'Z']
_CSPACE_AXES['lms'] = ['L', 'M', 'S']
_CSPACE_AXES['lab'] = ['L*', "a*", "b*"]
_CSPACE_AXES['luv'] = ['L*', "u*", "v*"]
_CSPACE_AXES['ipt'] = ['I', "P", "T"]
_CSPACE_AXES['wuv'] = ['W*', "U*", "V*"]
_CSPACE_AXES['Vrb_mb'] = ['V (Macleod-Boyton)', "r (Macleod-Boyton)", "b (Macleod-Boyton)"]
_CSPACE_AXES['cct'] = ['', 'cct','duv']
_CSPACE_AXES['srgb'] = ['sR', 'sG','sB']

# pre-calculate matrices for conversion of xyz to lms and back for use in xyz_to_ipt() and ipt_to_xyz():
_IPT_M = {'lms2ipt': np.array([[0.4000,0.4000,0.2000],[4.4550,-4.8510,0.3960],[0.8056,0.3572,-1.1628]]),
                              'xyz2lms' : {x : math.normalize_3x3_matrix(_CMF[x]['M'],spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = x)) for x in sorted(_CMF['types'])}}
_COLORTF_DEFAULT_WHITE_POINT = np.array([[100.0, 100.0, 100.0]]) # ill. E white point

#------------------------------------------------------------------------------
#---chromaticity coordinates---------------------------------------------------
#------------------------------------------------------------------------------
def xyz_to_Yxy(xyz, **kwargs):
    """
    Convert XYZ tristimulus values CIE Yxy chromaticity values.

    Args:
        :xyz: 
            | ndarray with tristimulus values

    Returns:
        :Yxy: 
            | ndarray with Yxy chromaticity values
            |  (Y value refers to luminance or luminance factor)
    """
    xyz = np2d(xyz)
    Yxy = np.empty(xyz.shape)
    sumxyz = xyz[...,0] + xyz[...,1] + xyz[...,2]
    Yxy[...,0] = xyz[...,1]
    Yxy[...,1] = xyz[...,0] / sumxyz
    Yxy[...,2] = xyz[...,1] / sumxyz
    return Yxy


def Yxy_to_xyz(Yxy, **kwargs):
    """
    Convert CIE Yxy chromaticity values to XYZ tristimulus values.

    Args:
        :Yxy: 
            | ndarray with Yxy chromaticity values
            |  (Y value refers to luminance or luminance factor)

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    Yxy = np2d(Yxy)
    xyz = np.empty(Yxy.shape)
    xyz[...,1] = Yxy[...,0]
    xyz[...,0] = Yxy[...,0]*Yxy[...,1]/Yxy[...,2]
    xyz[...,2] = Yxy[...,0]*(1.0-Yxy[...,1]-Yxy[...,2])/Yxy[...,2]
    return xyz

def xyz_to_Yuv(xyz,**kwargs):
    """
    Convert XYZ tristimulus values CIE 1976 Yu'v' chromaticity values.

    Args:
        :xyz: 
            | ndarray with tristimulus values

    Returns:
        :Yuv: 
            | ndarray with CIE 1976 Yu'v' chromaticity values
            |  (Y value refers to luminance or luminance factor)
    """
    xyz = np2d(xyz)
    Yuv = np.empty(xyz.shape)
    denom = xyz[...,0] + 15.0*xyz[...,1] + 3.0*xyz[...,2]
    Yuv[...,0] = xyz[...,1]
    Yuv[...,1] = 4.0*xyz[...,0] / denom
    Yuv[...,2] = 9.0*xyz[...,1] / denom
    return Yuv


def Yuv_to_xyz(Yuv, **kwargs):
    """
    Convert CIE 1976 Yu'v' chromaticity values to XYZ tristimulus values.

    Args:
        :Yuv: 
            | ndarray with CIE 1976 Yu'v' chromaticity values
            |  (Y value refers to luminance or luminance factor)

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    Yuv = np2d(Yuv)
    xyz = np.empty(Yuv.shape)
    xyz[...,1] = Yuv[...,0]
    xyz[...,0] = Yuv[...,0]*(9.0*Yuv[...,1])/(4.0*Yuv[...,2])
    xyz[...,2] = Yuv[...,0]*(12.0 - 3.0*Yuv[...,1] - 20.0*Yuv[...,2])/(4.0*Yuv[...,2])
    return xyz


def xyz_to_wuv(xyz, xyzw = _COLORTF_DEFAULT_WHITE_POINT, **kwargs):
    """
    Convert XYZ tristimulus values CIE 1964 U*V*W* color space.

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :xyzw: 
            | ndarray with tristimulus values of white point, optional
            |  (Defaults to luxpy._COLORTF_DEFAULT_WHITE_POINT)

    Returns:
        :wuv: 
            | ndarray with W*U*V* values
    """
    Yuv = xyz_to_Yuv(np2d(xyz)) # convert to cie 1976 u'v'
    Yuvw = xyz_to_Yuv(np2d(xyzw))
    wuv = np.empty(xyz.shape)
    wuv[...,0] = 25.0*(Yuv[...,0]**(1/3)) - 17.0
    wuv[...,1] = 13.0*wuv[...,0]*(Yuv[...,1] - Yuvw[...,1])
    wuv[...,2] = 13.0*wuv[...,0]*(Yuv[...,2] - Yuvw[...,2])*(2.0/3.0) #*(2/3) to convert to cie 1960 u, v
    return wuv

def wuv_to_xyz(wuv,xyzw = _COLORTF_DEFAULT_WHITE_POINT, **kwargs):
    """
    Convert CIE 1964 U*V*W* color space coordinates to XYZ tristimulus values.

    Args:
        :wuv: 
            | ndarray with W*U*V* values
        :xyzw: 
            | ndarray with tristimulus values of white point, optional
            |  (Defaults to luxpy._COLORTF_DEFAULT_WHITE_POINT)

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    wuv = np2d(wuv)
    Yuvw = xyz_to_Yuv(xyzw) # convert to cie 1976 u'v'
    Yuv = np.empty(wuv.shape)
    Yuv[...,0] = ((wuv[...,0] + 17.0) / 25.0)**3.0
    Yuv[...,1] = Yuvw[...,1] + wuv[...,1]/(13.0*wuv[...,0])
    Yuv[...,2] = Yuvw[...,2] + wuv[...,2]/(13.0*wuv[...,0]) * (3.0/2.0) # convert to cie 1960 u, v
    return Yuv_to_xyz(Yuv)


def xyz_to_xyz(xyz, **kwargs):
    """
    Convert XYZ tristimulus values to XYZ tristimulus values.

    Args:
        :xyz: 
            | ndarray with tristimulus values

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    return np2d(xyz)


def xyz_to_lms(xyz, cieobs = _CIEOBS, M = None, **kwargs):
    """
    Convert XYZ tristimulus values to LMS cone fundamental responses.

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :cieobs: 
            | _CIEOBS or str, optional
        :M: 
            | None, optional
            | Conversion matrix for xyz to lms.
            |   If None: use the one defined by :cieobs:

    Returns:
        :lms: 
            | ndarray with LMS cone fundamental responses
    """
    xyz = np2d(xyz)

    if M is None:
        M = _CMF[cieobs]['M']

    # convert xyz to lms:
    if len(xyz.shape) == 3:
        lms = np.einsum('ij,klj->kli', M, xyz)
    else:
        lms = np.einsum('ij,lj->li', M, xyz)
    return lms


def lms_to_xyz(lms, cieobs = _CIEOBS, M = None, **kwargs):
    """
    Convert LMS cone fundamental responses to XYZ tristimulus values.

    Args:
        :lms: 
            | ndarray with LMS cone fundamental responses
        :cieobs:
            | _CIEOBS or str, optional
        :M: 
            | None, optional
            | Conversion matrix for xyz to lms.
            |   If None: use the one defined by :cieobs:

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    lms = np2d(lms)

    if M is None:
        M = _CMF[cieobs]['M']

    # convert from lms to xyz:
    if len(lms.shape) == 3:
        xyz = np.einsum('ij,klj->kli', np.linalg.inv(M), lms)
    else:
        xyz = np.einsum('ij,lj->li', np.linalg.inv(M), lms)
    
    return xyz



def xyz_to_lab(xyz, xyzw = None, cieobs = _CIEOBS, **kwargs):
    """
    Convert XYZ tristimulus values to CIE 1976 L*a*b* (CIELAB) coordinates.

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :xyzw:
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw.

    Returns:
        :lab: 
            | ndarray with CIE 1976 L*a*b* (CIELAB) color coordinates
    """
    xyz = np2d(xyz)

    if xyzw is None:
        xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'], cieobs = cieobs)

    # get and normalize (X,Y,Z) to white point:
    XYZr = xyz/xyzw

    # Apply cube-root compression:
    fXYZr = XYZr**(1.0/3.0)

    # Check for T/Tn <= 0.008856: (Note (24/116)**3 = 0.008856)
    pqr = XYZr<=(24/116)**3

    # calculate f(T) for T/Tn <= 0.008856: (Note:(1/3)*((116/24)**2) = 841/108 = 7.787)
    fXYZr[pqr] = ((841/108)*XYZr[pqr]+16.0/116.0)

    # calculate L*, a*, b*:
    Lab = np.empty(xyz.shape)
    Lab[...,0] = 116.0*(fXYZr[...,1]) - 16.0
    Lab[pqr[...,1],0] = 903.3*XYZr[pqr[...,1],1]
    Lab[...,1] = 500.0*(fXYZr[...,0]-fXYZr[...,1])
    Lab[...,2] = 200.0*(fXYZr[...,1]-fXYZr[...,2])
    return Lab


def lab_to_xyz(lab, xyzw = None, cieobs = _CIEOBS, **kwargs):
    """
    Convert CIE 1976 L*a*b* (CIELAB) color coordinates to XYZ tristimulus values.

    Args:
        :lab: 
            | ndarray with CIE 1976 L*a*b* (CIELAB) color coordinates
        :xyzw:
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw.

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    lab = np2d(lab)

    if xyzw is None:
        xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = cieobs)

    # make xyzw same shape as data:
    xyzw = xyzw*np.ones(lab.shape)

    # get L*, a*, b* and Xw, Yw, Zw:
    fXYZ = np.empty(lab.shape)
    fXYZ[...,1] = (lab[...,0] + 16.0) / 116.0
    fXYZ[...,0] = lab[...,1] / 500.0 + fXYZ[...,1]
    fXYZ[...,2] = fXYZ[...,1] - lab[...,2]/200.0

    # apply 3rd power:
    xyz = (fXYZ**3.0)*xyzw

    # Now calculate T where T/Tn is below the knee point:
    pqr = fXYZ<=(24/116) #(24/116)**3**(1/3)
    xyz[pqr] = np.squeeze(xyzw[pqr]*((fXYZ[pqr] - 16.0/116.0) / (841/108)))

    return xyz



def xyz_to_luv(xyz, xyzw = None, cieobs = _CIEOBS, **kwargs):
    """
    Convert XYZ tristimulus values to CIE 1976 L*u*v* (CIELUV) coordinates.

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :xyzw:
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw.

    Returns:
        :luv: 
            | ndarray with CIE 1976 L*u*v* (CIELUV) color coordinates
    """
    xyz = np2d(xyz)

    if xyzw is None:
        xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = cieobs)

    # Calculate u',v' of test and white:
    Yuv = xyz_to_Yuv(xyz)
    Yuvw = xyz_to_Yuv(todim(xyzw, xyz.shape)) # todim: make xyzw same shape as xyz

    #uv1976 to CIELUV
    luv = np.empty(xyz.shape)
    YdivYw = Yuv[...,0] / Yuvw[...,0]
    luv[...,0] = 116.0*YdivYw**(1.0/3.0) - 16.0
    p = np.where(YdivYw <= (6.0/29.0)**3.0)
    luv[...,0][p] = ((29.0/3.0)**3.0)*YdivYw[p]
    luv[...,1] = 13.0*luv[...,0]*(Yuv[...,1]-Yuvw[...,1])
    luv[...,2] = 13.0*luv[...,0]*(Yuv[...,2]-Yuvw[...,2])
    return luv


def luv_to_xyz(luv, xyzw = None, cieobs = _CIEOBS, **kwargs):
    """
    Convert CIE 1976 L*u*v* (CIELUVB) coordinates to XYZ tristimulus values.

    Args:
        :luv: 
            | ndarray with CIE 1976 L*u*v* (CIELUV) color coordinates
        :xyzw:
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs: 
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw.

    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """
    luv = np2d(luv)

    if xyzw is None:
        xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = cieobs)

    # Make xyzw same shape as luv and convert to Yuv:
    Yuvw = todim(xyz_to_Yuv(xyzw), luv.shape, equal_shape = True)

    # calculate u'v' from u*,v*:
    Yuv = np.empty(luv.shape)
    Yuv[...,1:3] = (luv[...,1:3] / (13*luv[...,:1])) + Yuvw[...,1:3]
    Yuv[Yuv[...,0]==0,1:3] = 0

    Yuv[...,0] = Yuvw[...,0]*(((luv[...,0] + 16.0) / 116.0)**3.0)
    p = np.where((Yuv[...,0]/Yuvw[...,0]) < ((6.0/29.0)**3.0))
    Yuv[...,0][p] = Yuvw[...,0][p]*(luv[...,0][p]/((29.0/3.0)**3.0))

    return Yuv_to_xyz(Yuv)


#-------------------------------------------------------------------------------------------------
def xyz_to_Vrb_mb(xyz, cieobs = _CIEOBS, scaling = [1,1], M = None, **kwargs):
    """
    Convert XYZ tristimulus values to V,r,b (Macleod-Boynton) color coordinates.

    | Macleod Boynton: V = R+G, r = R/V, b = B/V
    | Note that R,G,B ~ L,M,S

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :cieobs: 
            | luxpy._CIEOBS, optional
            | CMF set to use when getting the default M, which is
              the xyz to lms conversion matrix.
        :scaling:
            | list of scaling factors for r and b dimensions.
        :M: 
            | None, optional
            | Conversion matrix for going from XYZ to RGB (LMS)
            |   If None, :cieobs: determines the M (function does inversion)

    Returns:
        :Vrb: 
            | ndarray with V,r,b (Macleod-Boynton) color coordinates

    Reference:
        1. `MacLeod DI, and Boynton RM (1979).
           Chromaticity diagram showing cone excitation by stimuli of equal luminance.
           J. Opt. Soc. Am. 69, 1183–1186.
           <https://www.osapublishing.org/josa/abstract.cfm?uri=josa-69-8-1183>`_
    """
    xyz = np2d(xyz)

    if M is None:
        M = _CMF[cieobs]['M']
        
    if len(xyz.shape) == 3:
        RGB = np.einsum('ij,klj->kli', M, xyz)
    else:
        RGB = np.einsum('ij,lj->li', M, xyz)
    Vrb = np.empty(xyz.shape)       
    Vrb[...,0] = RGB[...,0] + RGB[...,1]
    Vrb[...,1] = RGB[...,0] / Vrb[...,0] * scaling[0]
    Vrb[...,2] = RGB[...,2] / Vrb[...,0] * scaling[1]
    return Vrb


def Vrb_mb_to_xyz(Vrb,cieobs = _CIEOBS, scaling = [1,1], M = None, Minverted = False, **kwargs):
    """
    Convert V,r,b (Macleod-Boynton) color coordinates to XYZ tristimulus values.

    | Macleod Boynton: V = R+G, r = R/V, b = B/V
    | Note that R,G,B ~ L,M,S

    Args:
        :Vrb: 
            | ndarray with V,r,b (Macleod-Boynton) color coordinates
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when getting the default M, which is
            | the xyz to lms conversion matrix.
        :scaling:
            | list of scaling factors for r and b dimensions.
        :M: 
            | None, optional
            | Conversion matrix for going from XYZ to RGB (LMS)
            |   If None, :cieobs: determines the M (function does inversion)
        :Minverted:
            | False, optional
            | Bool that determines whether M should be inverted.

    Returns:
        :xyz: 
            | ndarray with tristimulus values

    Reference:
        1. `MacLeod DI, and Boynton RM (1979).
           Chromaticity diagram showing cone excitation by stimuli of equal luminance.
           J. Opt. Soc. Am. 69, 1183–1186.
           <https://www.osapublishing.org/josa/abstract.cfm?uri=josa-69-8-1183>`_
    """
    Vrb = np2d(Vrb)
    RGB = np.empty(Vrb.shape)
    RGB[...,0] = Vrb[...,1]*Vrb[...,0] / scaling[0]
    RGB[...,2] = Vrb[...,2]*Vrb[...,0] / scaling[1]
    RGB[...,1] = Vrb[...,0] - RGB[...,0]
    if M is None:
        M = _CMF[cieobs]['M']
    if Minverted == False:
        M = np.linalg.inv(M)
    
    if len(RGB.shape) == 3:
        return np.einsum('ij,klj->kli', M, RGB)
    else:
        return np.einsum('ij,lj->li', M, RGB)


def xyz_to_ipt(xyz, cieobs = _CIEOBS, xyzw = None, M = None, **kwargs):
    """
    Convert XYZ tristimulus values to IPT color coordinates.

    | I: Lightness axis, P, red-green axis, T: yellow-blue axis.

    Args:
        :xyz: 
            | ndarray with tristimulus values
        :xyzw: 
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw for rescaling M
            | (only when not None).
        :M: | None, optional
            | None defaults to xyz to lms conversion matrix determined by :cieobs:

    Returns:
        :ipt: 
            | ndarray with IPT color coordinates

    Note:
        :xyz: is assumed to be under D65 viewing conditions! If necessary perform chromatic adaptation !

    Reference:
        1. `Ebner F, and Fairchild MD (1998).
           Development and testing of a color space (IPT) with improved hue uniformity.
           In IS&T 6th Color Imaging Conference, (Scottsdale, Arizona, USA), pp. 8–13.
           <http://www.ingentaconnect.com/content/ist/cic/1998/00001998/00000001/art00003?crawler=true>`_
    """
    xyz = np2d(xyz)

    # get M to convert xyz to lms and apply normalization to matrix or input your own:
    if M is None:
        M = _IPT_M['xyz2lms'][cieobs].copy() # matrix conversions from xyz to lms
        if xyzw is None:
            xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = cieobs, out = 1)/100.0
        else:
            xyzw = xyzw/100.0
        M = math.normalize_3x3_matrix(M,xyzw)

    # get xyz and normalize to 1:
    xyz = xyz/100.0

    # convert xyz to lms:
    if np.ndim(M)==2:
        if len(xyz.shape) == 3:
            lms = np.einsum('ij,klj->kli', M, xyz)
        else:
            lms = np.einsum('ij,lj->li', M, xyz)
    else:
        if len(xyz.shape) == 3: # second dim of xyz must match dim of 1st of M and 1st dim of xyzw
            lms = np.concatenate([np.einsum('ij,klj->kli', M[i], xyz[:,i:i+1,:]) for i in range(M.shape[0])],axis=1)
        else: # first dim of xyz must match dim of 1st of M and 1st dim of xyzw
            lms = np.concatenate([np.einsum('ij,lj->li', M[i], xyz[i:i+1,:]) for i in range(M.shape[0])],axis=0)
        
    #lms = np.dot(M,xyz.T).T

    #response compression: lms to lms'
    lmsp = lms**0.43
    p = np.where(lms<0.0)
    lmsp[p] = -np.abs(lms[p])**0.43

    # convert lms' to ipt coordinates:
    if len(xyz.shape) == 3:
        ipt = np.einsum('ij,klj->kli', _IPT_M['lms2ipt'], lmsp)
    else:
        ipt = np.einsum('ij,lj->li', _IPT_M['lms2ipt'], lmsp)

    return ipt

def ipt_to_xyz(ipt, cieobs = _CIEOBS, xyzw = None, M = None, **kwargs):
    """
    Convert XYZ tristimulus values to IPT color coordinates.

    | I: Lightness axis, P, red-green axis, T: yellow-blue axis.

    Args:
        :ipt: 
            | ndarray with IPT color coordinates
        :xyzw:
            | None or ndarray with tristimulus values of white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating xyzw for rescaling Mxyz2lms
            | (only when not None).
        :M: | None, optional
            | None defaults to xyz to lms conversion matrix determined by:cieobs:

    Returns:
        :xyz: 
            | ndarray with tristimulus values

    Note:
        :xyz: is assumed to be under D65 viewing conditions! If necessary perform chromatic adaptation !

    Reference:
        1. `Ebner F, and Fairchild MD (1998).
           Development and testing of a color space (IPT) with improved hue uniformity.
           In IS&T 6th Color Imaging Conference, (Scottsdale, Arizona, USA), pp. 8–13.
           <http://www.ingentaconnect.com/content/ist/cic/1998/00001998/00000001/art00003?crawler=true>`_
    """
    ipt = np2d(ipt)

    # get M to convert xyz to lms and apply normalization to matrix or input your own:
    if M is None:
        M = _IPT_M['xyz2lms'][cieobs].copy() # matrix conversions from xyz to lms
        if xyzw is None:
            xyzw = spd_to_xyz(_CIE_ILLUMINANTS['D65'],cieobs = cieobs, out = 1)/100.0
        else:
            xyzw = xyzw/100.0
        M = math.normalize_3x3_matrix(M,xyzw)

    # convert from ipt to lms':
    if len(ipt.shape) == 3:
        lmsp = np.einsum('ij,klj->kli', np.linalg.inv(_IPT_M['lms2ipt']), ipt)
    else:
        lmsp = np.einsum('ij,lj->li', np.linalg.inv(_IPT_M['lms2ipt']), ipt)
        
    # reverse response compression: lms' to lms
    lms = lmsp**(1.0/0.43)
    p = np.where(lmsp<0.0)
    lms[p] = -np.abs(lmsp[p])**(1.0/0.43)

    # convert from lms to xyz:
    if np.ndim(M)==2:
        if len(ipt.shape) == 3:
            xyz = np.einsum('ij,klj->kli', np.linalg.inv(M), lms)
        else:
            xyz = np.einsum('ij,lj->li', np.linalg.inv(M), lms)
    else:
        if len(ipt.shape) == 3: # second dim of lms must match dim of 1st of M and 1st dim of xyzw
            xyz = np.concatenate([np.einsum('ij,klj->kli', np.linalg.inv(M[i]), lms[:,i:i+1,:]) for i in range(M.shape[0])],axis=1)
        else: # first dim of lms must match dim of 1st of M and 1st dim of xyzw
            xyz = np.concatenate([np.einsum('ij,lj->li', np.linalg.inv(M[i]), lms[i:i+1,:]) for i in range(M.shape[0])],axis=0)

    #xyz = np.dot(np.linalg.inv(M),lms.T).T
    xyz = xyz * 100.0
    xyz[np.where(xyz<0.0)] = 0.0

    return xyz

#------------------------------------------------------------------------------
def xyz_to_Ydlep(xyz, cieobs = _CIEOBS, xyzw = _COLORTF_DEFAULT_WHITE_POINT, flip_axes = False, **kwargs):
    """
    Convert XYZ tristimulus values to Y, dominant (complementary) wavelength
    and excitation purity.

    Args:
        :xyz:
            | ndarray with tristimulus values
        :xyzw:
            | None or ndarray with tristimulus values of a single (!) native white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating spectrum locus coordinates.
        :flip_axes:
            | False, optional
            | If True: flip axis 0 and axis 1 in Ydelep to increase speed of loop in function.
            |          (single xyzw with is not flipped!)
    Returns:
        :Ydlep: 
            | ndarray with Y, dominant (complementary) wavelength
            |  and excitation purity
    """
    
    xyz3 = np3d(xyz).copy().astype(np.float)

    # flip axis so that shortest dim is on axis0 (save time in looping):
    if (xyz3.shape[0] < xyz3.shape[1]) & (flip_axes == True):
        axes12flipped = True
        xyz3 = xyz3.transpose((1,0,2))
    else:
        axes12flipped = False

    # convert xyz to Yxy:
    Yxy = xyz_to_Yxy(xyz3)
    Yxyw = xyz_to_Yxy(xyzw)

    # get spectrum locus Y,x,y and wavelengths:
    SL = _CMF[cieobs]['bar']

    wlsl = SL[0]
    Yxysl = xyz_to_Yxy(SL[1:4].T)[:,None]

    # center on xyzw:
    Yxy = Yxy - Yxyw
    Yxysl = Yxysl - Yxyw
    Yxyw = Yxyw - Yxyw

    #split:
    Y, x, y = asplit(Yxy)
    Yw,xw,yw = asplit(Yxyw)
    Ysl,xsl,ysl = asplit(Yxysl)

    # calculate hue:
    h = math.positive_arctan(x,y, htype = 'deg')

    hsl = math.positive_arctan(xsl,ysl, htype = 'deg')

    hsl_max = hsl[0] # max hue angle at min wavelength
    hsl_min = hsl[-1] # min hue angle at max wavelength

    dominantwavelength = np.empty(Y.shape)
    purity = np.empty(Y.shape)
    for i in range(xyz3.shape[1]):

            # find index of complementary wavelengths/hues:
            pc = np.where((h[:,i] >= hsl_max) & (h[:,i] <= hsl_min + 360.0)) # hue's requiring complementary wavelength (purple line)
            h[:,i][pc] = h[:,i][pc] - np.sign(h[:,i][pc] - 180.0)*180.0 # add/subtract 180° to get positive complementary wavelength

            # find 2 closest hues in sl:
            #hslb,hib = meshblock(hsl,h[:,i:i+1])
            hib,hslb = np.meshgrid(h[:,i:i+1],hsl)
            dh = np.abs(hslb-hib)
            q1 = dh.argmin(axis=0) # index of closest hue
            dh[q1] = 1000.0
            q2 = dh.argmin(axis=0) # index of second closest hue

            dominantwavelength[:,i] = wlsl[q1] + np.divide(np.multiply((wlsl[q2] - wlsl[q1]),(h[:,i] - hsl[q1,0])),(hsl[q2,0] - hsl[q1,0])) # calculate wl corresponding to h: y = y1 + (y2-y1)*(x-x1)/(x2-x1)
            dominantwavelength[:,i][pc] = - dominantwavelength[:,i][pc] #complementary wavelengths are specified by '-' sign

            # calculate excitation purity:
            x_dom_wl = xsl[q1,0] + (xsl[q2,0] - xsl[q1,0])*(h[:,i] - hsl[q1,0])/(hsl[q2,0] - hsl[q1,0]) # calculate x of dom. wl
            y_dom_wl = ysl[q1,0] + (ysl[q2,0] - ysl[q1,0])*(h[:,i] - hsl[q1,0])/(hsl[q2,0] - hsl[q1,0]) # calculate y of dom. wl
            d_wl = (x_dom_wl**2.0 + y_dom_wl**2.0)**0.5 # distance from white point to sl
            d = (x[:,i]**2.0 + y[:,i]**2.0)**0.5 # distance from white point to test point
            purity[:,i] = d/d_wl

            # correct for those test points that have a complementary wavelength
            # calculate intersection of line through white point and test point and purple line:
            xy = np.vstack((x[:,i],y[:,i])).T
            xyw = np.hstack((xw,yw))
            xypl1 = np.hstack((xsl[0,None],ysl[0,None]))
            xypl2 = np.hstack((xsl[-1,None],ysl[-1,None]))
            da = (xy-xyw)
            db = (xypl2-xypl1)
            dp = (xyw - xypl1)
            T = np.array([[0.0, -1.0], [1.0, 0.0]])
            dap = np.dot(da,T)
            denom = np.sum(dap * db,axis=1,keepdims=True)
            num = np.sum(dap * dp,axis=1,keepdims=True)
            xy_linecross = (num/denom) *db + xypl1
            d_linecross = np.atleast_2d((xy_linecross[:,0]**2.0 + xy_linecross[:,1]**2.0)**0.5).T#[0]
            purity[:,i][pc] = d[pc]/d_linecross[pc][:,0]
    Ydlep = np.dstack((xyz3[:,:,1],dominantwavelength,purity))

    if axes12flipped == True:
        Ydlep = Ydlep.transpose((1,0,2))
    else:
        Ydlep = Ydlep.transpose((0,1,2))
    return Ydlep.reshape(xyz.shape)



def Ydlep_to_xyz(Ydlep, cieobs = _CIEOBS, xyzw = _COLORTF_DEFAULT_WHITE_POINT, flip_axes = False, **kwargs):
    """
    Convert Y, dominant (complementary) wavelength and excitation purity to XYZ
    tristimulus values.

    Args:
        :Ydlep: 
            | ndarray with Y, dominant (complementary) wavelength
              and excitation purity
        :xyzw: 
            | None or narray with tristimulus values of a single (!) native white point, optional
            | None defaults to xyz of CIE D65 using the :cieobs: observer.
        :cieobs:
            | luxpy._CIEOBS, optional
            | CMF set to use when calculating spectrum locus coordinates.
        :flip_axes:
            | False, optional
            | If True: flip axis 0 and axis 1 in Ydelep to increase speed of loop in function.
            |          (single xyzw with is not flipped!)
    Returns:
        :xyz: 
            | ndarray with tristimulus values
    """

    Ydlep3 = np3d(Ydlep).copy().astype(np.float)

    # flip axis so that longest dim is on first axis  (save time in looping):
    if (Ydlep3.shape[0] < Ydlep3.shape[1]) & (flip_axes == True):
        axes12flipped = True
        Ydlep3 = Ydlep3.transpose((1,0,2))
    else:
        axes12flipped = False

    # convert xyzw to Yxyw:
    Yxyw = xyz_to_Yxy(xyzw)
    Yxywo = Yxyw.copy()

    # get spectrum locus Y,x,y and wavelengths:
    SL = _CMF[cieobs]['bar']
    wlsl = SL[0,None].T
    Yxysl = xyz_to_Yxy(SL[1:4].T)[:,None]

    # center on xyzw:
    Yxysl = Yxysl - Yxyw
    Yxyw = Yxyw - Yxyw

    #split:
    Y, dom, pur = asplit(Ydlep3)
    Yw,xw,yw = asplit(Yxyw)
    Ywo,xwo,ywo = asplit(Yxywo)
    Ysl,xsl,ysl = asplit(Yxysl)

    # loop over longest dim:
    x = np.empty(Y.shape)
    y = np.empty(Y.shape)
    for i in range(Ydlep3.shape[1]):

        # find closest wl's to dom:
        #wlslb,wlib = meshblock(wlsl,np.abs(dom[i,:])) #abs because dom<0--> complemtary wl
        wlib,wlslb = np.meshgrid(np.abs(dom[:,i]),wlsl)

        dwl = np.abs(wlslb-wlib)
        q1 = dwl.argmin(axis=0) # index of closest wl
        dwl[q1] = 10000.0
        q2 = dwl.argmin(axis=0) # index of second closest wl

        # calculate x,y of dom:
        x_dom_wl = xsl[q1,0] + (xsl[q2,0] - xsl[q1,0])*(np.abs(dom[:,i]) - wlsl[q1,0])/(wlsl[q2,0] - wlsl[q1,0]) # calculate x of dom. wl
        y_dom_wl = ysl[q1,0] + (ysl[q2,0] - ysl[q1,0])*(np.abs(dom[:,i]) - wlsl[q1,0])/(wlsl[q2,0] - wlsl[q1,0]) # calculate y of dom. wl

        # calculate x,y of test:
        d_wl = (x_dom_wl**2.0 + y_dom_wl**2.0)**0.5 # distance from white point to dom
        d = pur[:,i]*d_wl
        hdom = math.positive_arctan(x_dom_wl,y_dom_wl,htype = 'deg')
        x[:,i] = d*np.cos(hdom*np.pi/180.0)
        y[:,i] = d*np.sin(hdom*np.pi/180.0)

        # complementary:
        pc = np.where(dom[:,i] < 0.0)
        hdom[pc] = hdom[pc] - np.sign(dom[:,i][pc] - 180.0)*180.0 # get positive hue angle

        # calculate intersection of line through white point and test point and purple line:
        xy = np.vstack((x_dom_wl,y_dom_wl)).T
        xyw = np.vstack((xw,yw)).T
        xypl1 = np.vstack((xsl[0,None],ysl[0,None])).T
        xypl2 = np.vstack((xsl[-1,None],ysl[-1,None])).T
        da = (xy-xyw)
        db = (xypl2-xypl1)
        dp = (xyw - xypl1)
        T = np.array([[0.0, -1.0], [1.0, 0.0]])
        dap = np.dot(da,T)
        denom = np.sum(dap * db,axis=1,keepdims=True)
        num = np.sum(dap * dp,axis=1,keepdims=True)
        xy_linecross = (num/denom) *db + xypl1
        d_linecross = np.atleast_2d((xy_linecross[:,0]**2.0 + xy_linecross[:,1]**2.0)**0.5).T[:,0]
        x[:,i][pc] = pur[:,i][pc]*d_linecross[pc]*np.cos(hdom[pc]*np.pi/180)
        y[:,i][pc] = pur[:,i][pc]*d_linecross[pc]*np.sin(hdom[pc]*np.pi/180)
    Yxy = np.dstack((Ydlep3[:,:,0],x + xwo, y + ywo))
    if axes12flipped == True:
        Yxy = Yxy.transpose((1,0,2))
    else:
        Yxy = Yxy.transpose((0,1,2))
    return Yxy_to_xyz(Yxy).reshape(Ydlep.shape)


def xyz_to_srgb(xyz, gamma = 2.4, **kwargs):
    """
    Calculates IEC:61966 sRGB values from xyz.

    Args:
        :xyz: 
            | ndarray with relative tristimulus values.
        :gamma: 
            | 2.4, optional
            | compression in sRGB

    Returns:
        :rgb: 
            | ndarray with R,G,B values (uint8).
    """

    xyz = np2d(xyz)

    # define 3x3 matrix
    M = np.array([[3.2404542, -1.5371385, -0.4985314],
                  [-0.9692660,  1.8760108,  0.0415560],
                  [0.0556434, -0.2040259,  1.0572252]])

    if len(xyz.shape) == 3:
        srgb = np.einsum('ij,klj->kli', M, xyz/100)
    else:
        srgb = np.einsum('ij,lj->li', M, xyz/100)

    # perform clipping:
    srgb[np.where(srgb>1)] = 1
    srgb[np.where(srgb<0)] = 0

    # test for the dark colours in the non-linear part of the function:
    dark = np.where(srgb <=  0.0031308)

    # apply gamma function:
    g = 1/gamma

    # and scale to range 0-255:
    rgb = srgb.copy()
    rgb = (1.055*rgb**g - 0.055) * 255

    # non-linear bit for dark colours
    rgb[dark]  = (srgb[dark].copy() * 12.92) * 255


    # clip to range:
    rgb[rgb>255] = 255
    rgb[rgb<0] = 0

    return rgb


def srgb_to_xyz(rgb, gamma = 2.4, **kwargs):
    """
    Calculates xyz from IEC:61966 sRGB values.

    Args:
        :rgb: 
            | ndarray with srgb values (uint8).
        :gamma: 
            | 2.4, optional
            | compression in sRGB
            
    Returns:
        :xyz: 
            | ndarray with relative tristimulus values.

    """
    rgb = np2d(rgb)
    
    # define 3x3 matrix
    M = np.array([[0.4124564,  0.3575761,  0.1804375],
                  [0.2126729,  0.7151522,  0.0721750],
                  [0.0193339,  0.1191920,  0.9503041]])

    # scale device coordinates:
    sRGB = rgb/255

    # test for non-linear part of conversion
    nonlin = np.where((rgb/255) <  0.0031308)#0.03928)

    # apply gamma function to convert to sRGB
    srgb = sRGB.copy()
    srgb = ((srgb + 0.055)/1.055)**gamma

    srgb[nonlin] = sRGB[nonlin]/12.92

    if len(srgb.shape) == 3:
        xyz = np.einsum('ij,klj->kli', M, srgb)*100
    else:
        xyz = np.einsum('ij,lj->li', M, srgb)*100
    return xyz

def xyz_to_jabz(xyz, **kwargs):
    """
    Convert XYZ tristimulus values to Jz,az,bz color coordinates.

    Args:
        :xyz: 
            | ndarray with absolute tristimulus values (Y in cd/m²!)

    Returns:
        :jabz: 
            | ndarray with Jz,az,bz color coordinates

    Notes:
     | 1. :xyz: is assumed to be under D65 viewing conditions! If necessary perform chromatic adaptation!
     |
     | 2a. Jz represents the 'lightness' relative to a D65 white with luminance = 10000 cd/m² 
     |      (note that Jz that not exactly equal 1 for this high value, but rather for 102900 cd/m2)
     | 2b.  az, bz represent respectively a red-green and a yellow-blue opponent axis 
     |      (but note that a D65 shows a small offset from (0,0))

    Reference:
        1. `Safdar, M., Cui, G., Kim,Y. J., and  Luo,M. R. (2017).
            Perceptually uniform color space for image signals including high dynamic range and wide gamut.
            Opt. Express, vol. 25, no. 13, pp. 15131–15151, Jun. 2017.
            <http://www.opticsexpress.org/abstract.cfm?URI=oe-25-13-15131>`_    
    """
    xyz = np2d(xyz)
    
    # Setup X,Y,Z to X',Y',Z' transform as matrix:
    b = 1.15
    g = 0.66
    M_to_xyzp = np.array([[b, 0, 1 - b],[1 - g, g, 0],[0, 0, 1]])

    # Define X',Y',Z' to L,M,S conversion matrix:
    M_to_lms = np.array([[0.41478972, 0.579999, 0.0146480,],
                  [-0.2015100, 1.120649, 0.0531008],
                  [-0.0166008, 0.264800, 0.6684799]])
    
    # Premultiply M_to_xyzp and M_to_lms:
    M =  M_to_lms @ M_to_xyzp
    
    # Transform X,Y,Z to L,M,S:
    if len(xyz.shape) == 3:
        lms = np.einsum('ij,klj->kli', M, xyz)
    else:
        lms = np.einsum('ij,lj->li', M, xyz)
    
    # response compression: lms to lms'
    lmsp = ((3424/(2**12) + (2413/(2**7))*(lms/10000)**(2610/(2**14)))/(1 + (2392/(2**7))*((lms/10000)**(2610/(2**14)))))**(1.7*2523/(2**5))

    # Transform L',M',S' to Iabz:
    M = np.array([[0.5, 0.5, 0],
                  [3.524000, -4.066708, 0.542708],
                  [0.199076, 1.096799, -1.295875]])
    if len(lms.shape) == 3:
        Iabz = np.einsum('ij,klj->kli', M, lmsp)
    else:
        Iabz = np.einsum('ij,lj->li', M, lmsp)

    # convert Iabz' to Jabz coordinates:

    Iabz[...,0] = ((1-0.56)*Iabz[...,0]/(1-0.56*Iabz[...,0])) - 1.6295499532821566e-11
    return Iabz

def jabz_to_xyz(jabz, **kwargs):
    """
    Convert Jz,az,bz color coordinates to XYZ tristimulus values.

    Args:
        :jabz: 
            | ndarray with Jz,az,bz color coordinates
            
    Returns:
        :xyz: 
            | ndarray with tristimulus values

    Note:
     | 1. :xyz: is assumed to be under D65 viewing conditions! If necessary perform chromatic adaptation!
     |
     | 2a. Jz represents the 'lightness' relative to a D65 white with luminance = 10000 cd/m² 
     |      (note that Jz that not exactly equal 1 for this high value, but rather for 102900 cd/m2)
     | 2b.  az, bz represent respectively a red-green and a yellow-blue opponent axis 
     |      (but note that a D65 shows a small offset from (0,0))


    Reference:
        1. `Safdar, M., Cui, G., Kim,Y. J., and  Luo,M. R. (2017).
            Perceptually uniform color space for image signals including high dynamic range and wide gamut.
            Opt. Express, vol. 25, no. 13, pp. 15131–15151, Jun. 2017.
            <http://www.opticsexpress.org/abstract.cfm?URI=oe-25-13-15131>`_    
    """
    jabz = np2d(jabz)
    
    # Convert Jz to Iz:
    jabz[...,0] = (jabz[...,0] + 1.6295499532821566e-11)/(1 - 0.56*(1 - (jabz[...,0] + 1.6295499532821566e-11)))

    # Convert Iabz to lmsp:
    M = np.linalg.inv(np.array([[0.5, 0.5, 0],
                  [3.524000, -4.066708, 0.542708],
                  [0.199076, 1.096799, -1.295875]]))
    
    if len(jabz.shape) == 3:
        lmsp = np.einsum('ij,klj->kli', M, jabz)
    else:
        lmsp = np.einsum('ij,lj->li', M, jabz)
        
    # Convert lmsp to lms:

    lms = 10000*(((3424/2**12) - lmsp**(1/(1.7*2523/2**5))) / (((2392/2**7)*lmsp**(1/(1.7*2523/2**5))) - (2413/2**7)))**(1/(2610/(2**14)))
    
    # Convert lms to xyz:
    # Setup X',Y',Z' from X,Y,Z transform as matrix:
    b = 1.15
    g = 0.66
    M_to_xyzp = np.array([[b, 0, 1 - b],[1 - g, g, 0],[0, 0, 1]])
    
    # Define X',Y',Z' to L,M,S conversion matrix:
    M_to_lms = np.array([[0.41478972, 0.579999, 0.0146480],
                  [-0.2015100, 1.120649, 0.0531008],
                  [-0.0166008, 0.264800, 0.6684799]])
    
    # Premultiply M_to_xyzp and M_to_lms and invert:
    M = M_to_lms @ M_to_xyzp
    M = np.linalg.inv(M)
    
    # Transform L,M,S to X,Y,Z:
    if len(jabz.shape) == 3:
        xyz = np.einsum('ij,klj->kli', M, lms)
    else:
        xyz = np.einsum('ij,lj->li', M, lms)
        
    return xyz