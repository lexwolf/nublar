#include <boost/math/special_functions/spherical_harmonic.hpp>
#include <complex_bessel.h>

using namespace sp_bessel;
std::complex<double> img=std::complex<double> (0,1.);

// Bessel Functions.
std::complex<double> j (double order, std::complex<double> x){
    return sph_besselJ(order,x);
    }
std::complex<double> h1 (double order, std::complex<double> x){
    return sph_hankelH1(order, x);
    }

// Riccati-Bessel Functions.
std::complex<double> RBj (double order, std::complex<double> x){
    return x*sph_besselJ(order,x);
    }
std::complex<double> RBj_prime(double order, std::complex<double> x){
    return (x*sph_besselJ(order-1,x)-order*sph_besselJ(order,x));
    }

std::complex<double> RBh (double order, std::complex<double> x){
    return x*sph_hankelH1(order, x);
    }
std::complex<double> RBh_prime (double order, std::complex<double> x){
//     return ((RBh(order,x+1.e-4)-RBh(order,x-1.e-4))/2.e-4);
    return (x*sph_hankelH1(order-1,x)-order*sph_hankelH1(order,x));
//     return std::complex<double> (0.,0.);
    }


//E_n
std::complex<double> E(int n, std::complex <double> E0){
    return pow(img,n)*(2.*n+1.)*E0/(n*(n+1.));
}
std::complex<double> Gwiggly(double order, double G, std::complex <double> E0, double T2){
    std::complex<double> GG;
    //GG = -img*fabs(G)*E(order, E0)/T2;
    GG = -img*fabs(G)/T2;
     if (norm(GG)<=1.e-60) GG = std::complex<double> (1.e-60, 1.e-60);
    return GG;
}
