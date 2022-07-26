# -*- coding: utf-8 -*-

### Primary functions of the Li et al. (2006) method
## Li et al. (2006) minimization method
def psi_lietal(IPSI,IPHI,DX,DY,U,V,ZBC='closed',MBC='closed',ALPHA=1.0e-14):

    """
    Compute streamfunction implementing 
    Li et al. (2006) method. Its advantages consist in
    extract the non-divergent and non-rotational part 
    of the flow without explicitly applying boundary 
    conditions and computational efficiency.
    This method also minimizes the difference between the
    reconstructed and original velocity fields. Therefore 
    it is ideal for large and non-regular domains with complex 
    coastlines and islands.
    Streamfunction and velocity potential are staggered with the 
    velocity components.
    Input:
            IPSI [M,N]		: Streamfunction initial guess
            IPHI [M,N]      : Velocity potential initial guess
            DX 	 [M,N]      : Zonal distance (i.e., resolution) 
            DY   [M,N]      : Meridional distance (i.e., resolution)
            U    [M-1,N-1]  : Original zonal velocity field defined between PSI and PHI grid points 
            V    [M-1,N-1]  : Original meridional velocity field defined between PSI and PHI grid points
    Optional Input:
            ZBC				: Zonal Boundary Condition for domain edge (closed or periodic)
            MBC				: Meridional Boundary Condition for domain edge (closed or periodic)
            ALPHA 			: Regularization parameter
    Output:
            psi [M,N]		: Streamfunction
            phi [M,N]		: Velocity Potential
    Obs1: PSI and PHI over land and boundaries have to be 0.0
    for better performance. However U and V can be masked with 
    NaNs 
    Obs2: Definitions
    U = dPsi/dy + dPhi/dx
    V = -dPsi/dx + dPhi/dy 
    Obs3: BCs are applied only to the Jacobian of the
    minimization function and are referred to the edges
    of the rectangular domain.  
    """

    ## Required packages
    import numpy as np 
    import scipy.optimize as optimize
    import time


    ## Reshape/Resize variables ("Vectorization")
    # Velocity
    M,N = U.shape

    y = np.ones(2*M*N)*np.nan

    # Velocity y = (U11,U12,...,U31,U32,....,V11,V12,....)
    y[:y.shape[0]//2] = U.reshape(M*N)
    y[y.shape[0]//2:] = V.reshape(M*N)

    idata = ~np.isnan(y.copy())
    y = y[idata]


    # Stream function and velocity potential
    M1,N1 = IPSI.shape

    x = np.ones(2*M1*N1)*np.nan

    # PSI and PHI vector: x = (PSI11,PSI12,...,PSI31,PSI32,...,PHI11,PHI12,...)
    x[:x.shape[0]//2] = IPSI.reshape(M1*N1)
    x[x.shape[0]//2:] = IPHI.reshape(M1*N1)		


    print('       Optimization process')
    t0 = time.clock()
    pq = optimize.minimize(ja,x,method='L-BFGS-B',jac=grad_ja,
        args=(y,DX,DY,M1,N1,idata,ZBC,MBC,ALPHA),options={'gtol': 1e-16})

    t1 = time.clock()

    print('           Time for convergence: %1.2f min'%((t1-t0)/60.0))
    print('           F(x): %1.2f'%(pq.fun))		

    psi = pq.x[:x.shape[0]//2].reshape((M1,N1))
    phi = pq.x[x.shape[0]//2:].reshape((M1,N1))

    return psi,phi



# Function to be minimized: Objective functional + Tikhonov's regularization term 
def ja(x,y,DX,DY,M1,N1,IDATA,ZBC,MBC,ALPHA):

    """
    Fitting function from Li et al (2006) method
    """

    ## Required packages
    import numpy as np

    # Derive velocity from PSI and PHI
    Ax = derive_ax(x,DX,DY,M1,N1,IDATA) 

    # "Error" to be minimized
    e = y.copy()-Ax

    # Matrices multiplications
    Mat1 = np.matmul(e.T,e)
    Mat2 = np.matmul(x.T,x)

    # Tikhionov's functional
    J = np.dot(0.5,Mat1) + np.dot(ALPHA*0.5,Mat2)

    return J


# Gradient of ja (i. e., Jacobian of ja)
# following Li et al method A.T(y-Ax) + alpha x.
# In our case, since Ax compute the velocity
# from the psi and phi, A.T(y-Ax) will be
# the curl and -divergent of the velocity difference 
# i.e., (zeta_o - zeta_r) and (div_r - div_o) 
def grad_ja(x,y,DX,DY,M1,N1,IDATA,ZBC,MBC,ALPHA):

    """
    Jacobian of the fitting function ja from Li et al (2006) method
    """

    ## Required packages
    import numpy as np


    # Derive velocity from PSI and Qi
    Ax = derive_ax(x,DX,DY,M1,N1,IDATA) 

    # "Error" to be minimized
    e = y-Ax

    # Compute adjoint term 
    # i. e., velocity difference curl and
    # velocity difference divergence
    adj = derive_adj(e,DX,DY,M1,N1,ZBC,MBC,IDATA)

    # Jacobian
    gj = -adj+np.dot(ALPHA,x)

    return gj



# Derive velocity components 
# from psi phi field 
def derive_ax(x,DX,DY,M1,N1,IDATA):

    """
    Derive velocity from psi and phi fields for the Li et al (2006) method
    """

    ## Required packages
    import numpy as np

    ## Re-organize x
    psi = x[:M1*N1].reshape((M1,N1))
    phi = x[M1*N1:].reshape((M1,N1))

    ## Derivation
    dpsidy = (psi[1:,:]-psi[:-1,:])/((DY[1:,:]+DY[:-1,:])/2.0)
    dpsidx = (psi[:,1:]-psi[:,:-1])/((DX[:,1:]+DX[:,:-1])/2.0)

    dphidy = (phi[1:,:]-phi[:-1,:])/((DY[1:,:]+DY[:-1,:])/2.0)
    dphidx = (phi[:,1:]-phi[:,:-1])/((DX[:,1:]+DX[:,:-1])/2.0)

    u = ((dpsidy[:,1:]+dpsidy[:,:-1])/2.0) + ((dphidx[1:,:] + dphidx[:-1,:]) /2.0)
    v = (-(dpsidx[1:,:]+dpsidx[:-1,:])/2.0) + ((dphidy[:,1:] + dphidy[:,:-1]) /2.0)

    # Organize the variables
    ax = np.ones(2*(M1-1)*(N1-1))*np.nan
    ax[:ax.shape[0]//2] = u.reshape((M1-1)*(N1-1))
    ax[ax.shape[0]//2:] = v.reshape((M1-1)*(N1-1))

    # Remove NaNs
    ax = ax[IDATA]

    return ax




# Derive the adjoint term
# (i. e., relative vorticity)
def derive_adj(e,DX,DY,M1,N1,ZBC,MBC,IDATA):

    """
    Derive the adjoint term of the Li et al (2006) method
    """

    ## Required packages
    import numpy as np

    ## Resized error
    er = np.zeros(2*(M1-1)*(N1-1))
    er[IDATA] = e.copy()


    ## Re-organize variables
    # Velocity
    u = er[:er.shape[0]//2]
    v = er[er.shape[0]//2:]

    u = u.reshape((M1-1,N1-1))
    v = v.reshape((M1-1,N1-1))

    # Spatial resolution, note that u/v is on q-point!
    dy = (DY[1:-1,1:]+DY[1:-1,:-1])/2.0  # on u-point
    dx = (DX[1:,1:-1]+DX[:-1,1:-1])/2.0  # on v-point

    ## Derivation of the curl and divergence, defined on p-points but with [-2 -2] size
    # Curl terms
    dudy = (u[1:,:]-u[:-1,:])/dy
    dudy = (dudy[:,1:]+dudy[:,:-1])/2.0

    dvdx = (v[:,1:]-v[:,:-1])/dx
    dvdx = (dvdx[1:,:]+dvdx[:-1,:])/2.0

    # Divergent terms
    dvdy = (v[1:,:]-v[:-1,:])/dy
    dvdy = (dvdy[:,1:]+dvdy[:,:-1])/2.0

    dudx = (u[:,1:]-u[:,:-1])/dx
    dudx = (dudx[1:,:]+dudx[:-1,:])/2.0	


    # Curl
    curl = dvdx-dudy
    curl1 = np.ones((M1,N1))*np.nan
    curl1[1:-1,1:-1] = curl


    # Divergence
    div = dudx+dvdy
    div1 = np.ones((M1,N1))*np.nan
    div1[1:-1,1:-1] = div


    ## Calculate boundary conditions for 
    ## the curl and divergence fields
    if ZBC == 'periodic' or MBC == 'periodic':

        if ZBC == 'periodic':

            # Curl
            dudy_1 = (u[1:,0]-u[:-1,0])/dy[:,0]
            dudy_2 = (u[1:,-1]-u[:-1,-1])/dy[:,-1]

            dvdx_1 = (v[:,0]-v[:,-1])/dx[:,0]
            dvdx_2 = dvdx_1.copy() 

            curl1[1:-1,0] = ((dvdx_1[1:]+dvdx_1[:-1])/2.0)-dudy_1
            curl1[1:-1,-1] = ((dvdx_2[1:]+dvdx_2[:-1])/2.0)-dudy_2


            # Divergent
            dvdy_1 = (v[1:,0]-v[:-1,0])/dy[:,0]
            dvdy_2 = (v[1:,-1]-v[:-1,-1])/dy[:,-1]

            dudx_1 = (u[:,0]-u[:,-1])/dx[:,0]
            dudx_2 = dudx_1.copy()

            div1[1:-1,0] = ((dudx_1[1:]+dudx_1[:-1])/2.0)+dvdy_1
            div1[1:-1,-1] = ((dudx_2[1:]+dudx_2[:-1])/2.0)+dvdy_2

        else:
            curl1[:,0] = curl1[:,1]; curl1[:,-1] = curl1[:,-2]
            div1[:,0] = div1[:,1]; div1[:,-1] = div1[:,-2]


        if MBC == 'periodic':

            # Curl
            dudy_1 = (u[0,:]-u[-1,:])/dy[0,:]
            dudy_2 = dudy_1.copy()

            dvdx_1 = (v[0,1:]-v[0,:-1])/dx[0,:]
            dvdx_2 = (v[-1,1:]-v[-1,:-1])/dx[-1,:]

            curl1[0,1:-1] = dvdx_1-((dudy_1[1:]+dudy_1[:-1])/2.0)
            curl1[-1,1:-1] = dvdx_2-((dudy_2[1:]+dudy_2[:-1])/2.0)


            # Divergent 
            dvdy_1 = (v[0,:]-v[-1,:])/dy[0,:]
            dvdy_2 = dvdy_1.copy()

            dudx_1 = (u[0,1:]-u[0,:-1])/dx[0,:]
            dudx_2 = (u[-1,1:]-u[-1,:-1])/dx[-1,:]

            div1[0,1:-1] = dudx_1 + ((dvdy_1[1:]+dvdy_1[:-1])/2.0)
            div1[-1,1:-1] = dudx_2 + ((dvdy_2[1:]+dvdy_2[:-1])/2.0)

        else:

            curl1[0,:] = curl1[1,:]; curl1[-1,:] = curl1[-2,:]
            div1[0,:] = div1[1,:]; div1[-1,:] = div1[-2,:]

    else:

        # All closed edges (i.e., land edges)
        # curl1 and div1 on the edge points are same with the adjacent points
        curl1[0,1:-1] = curl[0,:]; curl1[-1,1:-1] = curl[-1,:]
        curl1[:,0] = curl1[:,1]; curl1[:,-1] = curl1[:,-2]

        div1[0,1:-1] = div[0,:]; div1[-1,1:-1] = div[-1,:]
        div1[:,0] = div1[:,1]; div1[:,-1] = div1[:,-2]


    # Organize the variables
    curl = curl1.reshape(M1*N1)
    div = div1.reshape(M1*N1)

    adj = np.ones(2*M1*N1)*np.nan
    adj[:M1*N1] = curl
    adj[M1*N1:] = -div

    return adj





### Auxiliary Functions
## Cumulative velocity integration
def v_zonal_integration(V,DX):
    """
    Zonal cumulative integration of velocity
    in a rectangular grid using a trapezoidal
    numerical scheme. 
    - Integration occurs from east to west
    - Velocity is assumed to be zero at the lateral
    boundaries defined by NaN.
    Input:
            V   [M,N]: meridional velocity component in m s-1
            DX 	[M,N-1]: zonal distance in m
    Output: 
            vi [M,N]: Integrated velocity in m2 s-1
    """

    ## Required packages
    import numpy as np

    ## Zero velocity at the boundaries
    v = V.copy()

    ibad = np.isnan(v)
    v[ibad] = 0.0

    ## Zonal integration	
    vi = np.zeros(v.shape)

    for j in range(2,vi.shape[1]+1):
        vi[:,-j] = np.trapz(v[:,-j:], dx=DX[:,(-j+1):])

    return vi



def v_meridional_integration(V,DY):
    """
    Meridional cumulative integration of velocity
    in a rectangular grid using a trapezoidal
    numerical scheme. 
    - Integration occurs from north to south
    - Velocity is assumed to be zero at the lateral
    boundaries defined by NaN.
    Input:
            V   [M,N]: meridional velocity component in m s-1
            DY 	[M-1,N]: zonal distance in m
    Output: 
            vi [M,N]: Integrated velocity in m2 s-1
    """

    ## Required packages
    import numpy as np

    ## Zero velocity at the boundaries
    v = V.copy()

    ibad = np.isnan(v)
    v[ibad] = 0.0

    ## Zonal integration	
    vi = np.zeros(v.shape)

    for i in range(2,vi.shape[0]+1):
        vi[-i,:] = np.trapz(v[-i:,:],dx=DY[(-i+1):,:],axis=0)

    return vi


## Calculate distances from a rectangular lat/lon grid
def dx_from_dlon(lon,lat):
    """
    Calculate zonal distance at the Earth's surface in m from a 
    longitude and latitude rectangular grid
    Input:
            lon [M,N]: Longitude in degrees
            lat [M,N]: Latitude in degrees
    Output:
            dx   [M,N-1]: Distance in meters
    """

    ## Required packages
    import numpy as np

    # Earth Radius in [m]
    earth_radius = 6371.0e3


    # Convert angles to radians
    lat = np.radians(lat)
    lon = np.radians(lon)

    # Zonal distance in radians
    dlon = np.diff(lon,axis=1)
    lat = (lat[:,1:]+lat[:,:-1])/2.0


    # Zonal distance arc 
    a = np.cos(lat)*np.cos(lat)*(np.sin(dlon/2.0))**2.0
    angles = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Distance in meters
    dx = earth_radius * angles

    return dx



def dy_from_dlat(lat):
    """
    Calculate meridional distance at the Earth's surface in m from a 
    longitude and latitude rectangular grid
    Input:
            lat [M,N]: Latitude in degrees
    Output:
            dy   [M-1,N]: Distance in meters
    """

    ## Required packages
    import numpy as np

    ## Meridional resolution (m)
    dy = np.diff(lat,axis=0)
    dy = dy*111194.928

    return dy

def periodify(X,Y,M):
    
    import numpy as np
    
    M = np.hstack([M[:,::-1],M,M[:,::-1]])
    M = np.vstack([M[::-1,:],M,M[::-1,:]])
    
    xr = X.max()-X.min()
    yr = Y.max()-Y.min()
    
    X = np.hstack([X-xr,X,X+xr])
    Y = np.vstack([Y-yr,Y,Y+yr])
    
    X = np.vstack([X,X,X])
    Y = np.hstack([Y,Y,Y])
    
    return X,Y,M

def integ(a):
    import numpy as np
    from scipy import integrate
    c = np.array([-integrate.simps(a[:i]) for i in np.arange(1,len(a)+1)])
    c = c-c.mean()
    return c

def uv2psiphi(LON,LAT,U,V,ZBC='closed',MBC='closed',ALPHA=1.0e-14,fac=111195,period=False):
    """
    Compute streamfunction implementing 
    Li et al. (2006) method. Its advantages consist in
    extract the non-divergent and non-rotational part 
    of the flow without explicitly applying boundary 
    conditions and computational efficiency.
    This method also minimizes the difference between the
    reconstructed and original velocity fields. Therefore 
    it is ideal for large and non-regular domains with complex 
    coastlines and islands.
    Streamfunction and velocity potential are staggered with the 
    velocity components.
    Input:
            LON   [M,N]      : Longitude
            LAT   [M,N]      : Latitude
            U    [M,N]  : Original zonal velocity field 
            V    [M,N]  : Original meridional velocity field
    Optional Input:
            ZBC             : Zonal Boundary Condition for domain edge (closed or periodic)
            MBC             : Meridional Boundary Condition for domain edge (closed or periodic)
            ALPHA           : Regularization parameter
            fac             : Distance of 1 degree in meters
    Output:
            psi     [M,N]: Streamfunction
            Upsi    [M,N]  : Nondivergent zonal velocity field
            Vpsi    [M,N]  : Nondivergent meridional velocity field
            phi     [M,N]: Velocity Potential
            Uphi    [M,N]  : Nonrotational zonal velocity field 
            Vphi    [M,N]  : Nonrotational meridional velocity field
    Obs1: PSI and PHI over land and boundaries have to be 0.0
    for better performance. However U and V can be masked with 
    NaNs 
    Obs2: Definitions
    U = dPsi/dy + dPhi/dx
    V = -dPsi/dx + dPhi/dy 
    Obs3: BCs are applied only to the Jacobian of the
    minimization function and are referred to the edges
    of the rectangular domain.  
    """

    ## Required packages
    import numpy as np 
    
    u = U.copy()
    v = V.copy()
    lon = LON.copy()
    lat = LAT.copy()
    
    if period:
        lon,lat,u = periodify(LON,LAT,u)
        _,_,v = periodify(LON,LAT,v)
    
    mask = np.isnan(u)

    u[mask] = 0
    v[mask] = 0

    psin = +np.array(list(map(integ,v*np.diff(lon[0]).mean()*fac)))-\
            np.array(list(map(integ,u.T*np.diff(lat.T[0]).mean()*fac))).T
    phin = -np.array(list(map(integ,u*np.diff(lon[0]).mean()*fac)))+\
            np.array(list(map(integ,v.T*np.diff(lat.T[0]).mean()*fac))).T

    # defined on q-points, [-1 -1] size compared to p-vars
    Um = (u[:,1:] + u[:,:-1]) / 2
    Um = (Um[1:,:] + Um[:-1,:]) / 2

    Vm = (v[:,1:] + v[:,:-1]) / 2
    Vm = (Vm[1:,:] + Vm[:-1,:]) / 2

    psi,phi = psi_lietal(psin,phin,np.gradient(lon)[1]*fac,np.gradient(lat)[0]*fac,Um,Vm,ZBC=ZBC,MBC=MBC,ALPHA=ALPHA)

    psi = -psi
    phi = -phi

    psi = psi-np.nanmean(psi)
    phi = phi-np.nanmean(phi)

    phiy,phix = np.gradient(phi)
    psiy,psix = np.gradient(psi)

    unr,vnr = -phix/(np.gradient(lon)[1]*fac),-phiy/(np.gradient(lat)[0]*fac)
    und,vnd = -psiy/(np.gradient(lat)[0]*fac),psix/(np.gradient(lon)[1]*fac)


    psi[mask] = np.nan
    phi[mask] = np.nan

    und[mask] = np.nan
    vnd[mask] = np.nan
    unr[mask] = np.nan
    vnr[mask] = np.nan
    
    if period:
        l,m = psi.shape[0]//3,psi.shape[1]//3
        psi,und,vnd,phi,unr,vnr = [a[l:-l,m:-m] for a in [psi,und,vnd,phi,unr,vnr]]

    return psi,und,vnd,phi,unr,vnr

