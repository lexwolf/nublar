#include <iostream>
#include <fstream>
#include <complex>
#include <vector>
#include <iomanip>
#define CUP_BACKEND_QUASI_STATIC
#include <nano_geo_matrix/core/mathNN.hpp>
#include <nano_geo_matrix/quasi_static/geometry/single.hpp>
#include <cup.hpp>
#include "effective_medium.hpp"
#include "project_paths.hpp"

/*
Example compilation:

NGM_ROOT=$(realpath ../extern/nano_geo_matrix)

g++ -std=c++17 \
  -I../header \
  -I../include \
  -I"$NGM_ROOT/include" \
  -I"$NGM_ROOT/modules/cup" \
  -I/usr/include/eigen3 \
  clausius-mossotti.cxx -lgsl -o ../bin/cm
*/

std::pair<double, double> getmax (std::vector<std::pair<double, double>> Data){
    std::pair<double, double> max=std::make_pair(0, -1e30);;
    
    for (const auto& data : Data)
        if (data.second>max.second) max=data;
        
    return max;
    }

using namespace std;

int main(int argc, char *argv[]) {
    std::string project_root = nublar::set_current_path_to_project_root(argv[0]);

    std::complex<double> eps1, eps_eff, enne;
    double effe, lamin, lamax, lam, dlam, omeeV, erre, eps2, nair, nglas=1.5, erre1, erre2;
    int Nlam=1000;
    std::vector<std::pair<double, double>> columnData;
    
    nanosphere su;
    su.init();
    su.set_metal("silver","spline",1);
    eps2    = su.set_host("air");
    nair    = sqrt(eps2);

    fstream isla, nblr;
    const std::string input_path = project_root + "/data/input/islas.dat";
    const std::string output_path = project_root + "/data/output/nublar.dat";
    isla.open(input_path, ios::in);
    if (!isla.is_open()) {
        std::cerr << "Error opening input file: " << input_path << std::endl;
        return 1;
    }
    nblr.open(output_path, ios::out);
    if (!nblr.is_open()) {
        std::cerr << "Error opening output file: " << output_path << std::endl;
        return 1;
    }
    
    if (!(isla >> lamin >> lamax >> effe)) {
        std::cerr << "Error reading simulation parameters from: " << input_path << std::endl;
        return 1;
    }
    
    dlam = (lamax - lamin)/Nlam;
    double L    = 80, absr;
    
    for (int i = 0; i <= Nlam; i++) {
        L = 100*effe;
        lam     = lamin+i*dlam;
        omeeV   = h*j2eV*cc/(lam*1.e-9);
        eps1    = su.metal(omeeV);
        eps_eff = nublar::MaxwellGarnett(effe, eps1, eps2);
        enne    = sqrt(eps_eff);
        erre    = norm((nair-enne)/(nair+enne)); // reflectance
        absr    = exp(-4.*M_PI*enne.imag()*L/lam);
        erre1   = norm((enne-nglas)/(enne+nglas)); // reflectance
        erre2   = norm((nair-nglas)/(nair+nglas)); // reflectance
        nblr<<lam<<" "<<(1-erre2)*(1-erre1)*((1-erre)*absr)<<" "<<eps_eff.real()<<" "<<eps_eff.imag()<<" "<<enne.real()<<" "<<enne.imag()<<endl;
        columnData.push_back(std::make_pair(lam, enne.imag()));
        }
    std::pair<double, double> maxValue = getmax(columnData);
    
    std::cout << std::fixed << std::setprecision(6)
                  << maxValue.first << " " << maxValue.second;
    return 0;
    }
