#include <iostream>
#include <fstream>
#include <complex>
#include <vector>
#include <iomanip>
#include <filesystem>
#define CUP_BACKEND_QUASI_STATIC
#include <nano_geo_matrix/core/mathNN.hpp>
#include <nano_geo_matrix/quasi_static/geometry/single.hpp>
#include <cup.hpp>

/*
Example compilation:

g++ -std=c++17 \
  -I../include \
  -I"$(realpath ../extern/nano_geo_matrix/include)" \
  -I"$(realpath ../extern/nano_geo_matrix/modules/cup)" \
  -I/usr/include/eigen3 \
  clausius-mossotti.cxx -lgsl -o ../bin/cm
*/

std::pair<double, double> getmax (std::vector<std::pair<double, double>> Data){
    std::pair<double, double> max=std::make_pair(0, -1e30);;
    
    for (const auto& data : Data)
        if (data.second>max.second) max=data;
        
    return max;
    }

std::complex<double>Maxwell_Garnett(double effe, std::complex<double> eps1, std::complex<double> eps2) {
    // Calculate the effective permittivity using theMaxwell_Garnett mixing rules
    std::complex<double> eps_eff;
    double small_number_cutoff = 1e-6;

    if (effe < 0 || effe > 1){
        std::cout<<"WARNING: volume portion of inclusion material is out of range!"<<std::endl;
        exit(-11);
        }
    std::complex<double> factor_up   = 2.*(1.-effe)*eps2+(1.+2.*effe)*eps1;
    std::complex<double> factor_down = (2.+effe)*eps2+(1.-effe)*eps1;
    if (norm(factor_down)<small_number_cutoff){
        std::cout<<"WARNING: the effective medium is singular"<<std::endl;
        exit(-22);
        } else eps_eff = eps2*factor_up/ factor_down;
    return eps_eff;
}

using namespace std;

int main(int argc, char *argv[]) {
    std::error_code ec;
    std::filesystem::path exec_path = std::filesystem::weakly_canonical(
        std::filesystem::absolute(argv[0]), ec);
    std::string project_root = ".";
    if (!ec && exec_path.has_parent_path()) {
        project_root = exec_path.parent_path().parent_path().string();
    }
    std::filesystem::current_path(project_root, ec);

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
        eps_eff = Maxwell_Garnett(effe, eps1, eps2);
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
