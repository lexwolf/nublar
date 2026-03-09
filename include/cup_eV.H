#include <complex>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <gsl/gsl_errno.h>
#include <gsl/gsl_spline.h>

#define cc  299792458.
/** c [m/s] Speed of light **/
#define h  6.626068e-34
/** h [m²kg/s] **/

#define he 6.62606957e-27 	
/** h [erg s] serve h nel sistema di Gauss**/

#define j2eV 6.24150636309e18
#define eV2j 1.60217733000103e-19
#define eV2erg 1.60217657e-12
#define erg2eV 6.24150932e11

double eV2nm(double ome){
  double lam;
  lam=cc/(ome*eV2j/h)*1.e9;
  return lam;
  }

class nanosphere{
    private:
	gsl_interp_accel *acc;
	gsl_interp_accel *ach;
	gsl_spline *reeps;
	gsl_spline *imeps;
	gsl_spline *reeph;
	gsl_spline *imeph;
	char *wrk;
    public:
	std::complex<double> img;
	double lrntz, act;
	double pi, vF, enha;
	double A, r1, r2, rap;
	double G;
	double ome_p, ome_L, tau_d, tau_L, Dome, lam_0, eps_0;
	double ome_p2,ome_L2, tau_d2, tau_L2, ome_0, gam, kap;
	double ome_o2, ome, f, n, enne;
	double Ome_p, Gam_d, Gam, eps_inf, Ome_L, Gam_L, Deps;
	std::complex<double> eps3;
	void init(){
	  /** all values are in MKS **/
	  img = std::complex<double> (0., 1.);
	  pi = acos(-1.);
	  }

	void set_metal(const char* mtl, const char* mdl, int sel=0){
	  /** Ome_p [THz]	Plasma frequency (gold)		**/
	  /** Ome_L [THz]	Lorentz frequency (gold)	**/
	  /** Gam_d [THz]	Drude damping coefficient (gold)**/
	  /** Gam_L [THz]	Lorentz spectral width (gold)	**/
	  /** Deps weighting factor.			**/
	  double *omem, *reps, *ieps, la, Dr, Di, lc;
	  char line [900], *jc;
	  int rows=0;
	  jc = new char [128];
	  if(strcmp(mtl,"gold")==0){
	      vF=1.39e6;
	      /** m/s **/
// 	      lc=5e-9; // va bene per lo spettro
// 	      lc=1.5e-8; // va bene per le misure sul setup senza pompa
	      lc=1.e-8; // va bene per le misure sul setup
// 	      Gam=h*j2eV*vF/(r1*2.*pi);
	      Gam=h*j2eV*vF/(lc*2.*pi);
// 	      std::cout<<r1<<" Gam = "<<Gam<<std::endl;
	      Ome_p=8.91;
	      Gam_d=0.0759;
// 	      std::cout<<"Gam_d = "<<Gam_d<<std::endl;
	      eps_inf=9.0685;
	      if(strcmp(mdl,"drude")==0){
		lrntz=0;
		} else if(strcmp(mdl,"drude-lorentz")==0){
		  if (sel==1){
		    Ome_p=8.91;//2113.6;
		    Gam_d=0.0759;//15.92;
		    eps_inf=5.9673;
		    Deps=1.09;
		    Ome_L=1.90724;//wait!!
		    Gam_L=11.8238;//wait!!
		    }
		  else if (sel==2){
		    Ome_p=2106.78;
		    Gam_d=2.46;
		    eps_inf=6.617;
		    Deps=1.73;
		    Ome_L=730.56;
		    Gam_L=222.0;
		}else exit(1);
		lrntz=1;
	      } else if(strcmp(mdl,"spline")==0){
		if (sel==1) strcpy(jc,"data/input/goldJCeV.dat");
		else if (sel==2) strcpy(jc,"data/input/goldWeV.dat");
		else exit(-1);
		std::fstream inp;
		inp.open(jc,std::ios::in);
		if (!inp.is_open()){
		  std::cerr<<"Error opening file "<<jc<<std::endl;
		  exit(1);
		  }
		while(!inp.eof()){
		  inp.getline (line,900);
		  rows++;
		  }
		inp.close();
		omem=new double [rows];
		reps=new double [rows];
		ieps=new double [rows];
		inp.open(jc, std::ios::in);
		for (int i=0; i<rows; i++)
		  inp>>la>>omem[i]>>reps[i]>>ieps[i]>>Dr>>Di;
		acc = gsl_interp_accel_alloc ();
		reeps = gsl_spline_alloc (gsl_interp_cspline, rows);
		imeps = gsl_spline_alloc (gsl_interp_cspline, rows);
		gsl_spline_init (reeps, omem, reps, rows);
		gsl_spline_init (imeps, omem, ieps, rows);
		lrntz=-1;
		}
	      else {
		std::cout<<"you chosed "<<mdl<<" while option for gold are: drude, drude-lorentz, spline"<<std::endl;
		exit(1);
		}
	    } else  if(strcmp(mtl,"silver")==0){
	      vF=1.39e6;
	      /** m/s **/
	      lc=1.e-8; // 
	      Gam=h*j2eV*vF/(lc*2.*pi);
// 	      std::cout<<r1<<" Gam = "<<Gam<<std::endl;
	      Ome_p=9.6;
	      Gam_d=0.0228;
// 	      std::cout<<"Gam_d = "<<Gam_d<<std::endl;
	      eps_inf=5.3;
		if(strcmp(mdl,"drude")==0){
		lrntz=0;
		} else if(strcmp(mdl,"spline")==0){
		strcpy(jc,"data/input/silverJCeV.dat");
		std::fstream inp;
		inp.open(jc,std::ios::in);
		if (!inp.is_open()){
		  std::cerr<<"Error opening file "<<jc<<std::endl;
		  exit(1);
		  }
		while(!inp.eof()){
		  inp.getline (line,900);
		  rows++;
		  }
		inp.close();
		omem=new double [rows];
		reps=new double [rows];
		ieps=new double [rows];

		inp.open(jc, std::ios::in);
		for (int i=0; i<rows; i++)
		  inp>>la>>omem[i]>>reps[i]>>ieps[i]>>Dr>>Di;
		acc = gsl_interp_accel_alloc ();
		reeps = gsl_spline_alloc (gsl_interp_cspline, rows);
		imeps = gsl_spline_alloc (gsl_interp_cspline, rows);
		gsl_spline_init (reeps, omem, reps, rows);
		gsl_spline_init (imeps, omem, ieps, rows);
		lrntz=-1;
		}
	      else {
		std::cout<<"you chosed "<<mdl<<" while option for silver are: spline"<<std::endl;
		exit(1);
		}
	    }
	    else{
		std::cout<<mtl<<" not found, option are: gold, silver"<<std::endl;
		exit(1);
		}
	  ome_p=Ome_p; //corretto
	  ome_L=Ome_L*1.e12;
	  tau_d=1./(Gam_d*1.e12);
	  tau_L=1./(Gam_L*1e12);
	  ome_p2=ome_p*ome_p;
	  ome_L2=ome_L*ome_L;
// 	  ome_0=h*j2eV*c/(lam_0*1.e-9); //corretto
	  ome_o2=ome_0*ome_0;
	  }

	double set_host(const char* hst){
	  double eps_0;
	  if(strcmp(hst,"silica")==0) eps_0 = 2.1316; // Si02
	  else if(strcmp(hst,"solgel")==0) eps_0 = 2.1331;//3.8
	  else if(strcmp(hst,"water")==0) eps_0 = 1.7689;
	  else if(strcmp(hst,"air")==0) eps_0 = 1.0006;
	  else if(strcmp(hst,"glass")==0) eps_0 = 1.2247;
	  else if(strcmp(hst,"PMMA")==0) eps_0 = 2.2201;
	  else if(strcmp(hst,"ethanol")==0) eps_0 = 1.8496;//1.1662;
	  else{
		std::cout<<"option are: silica, water, air, glass, PMMA, ethanol"<<std::endl;
		exit(1);
		}
	  return eps_0;
	  }
	  
	void set_active(const char* mod){
	  char line [900], *mc;
	  double *omem, *reph, *ieph;
	  int rows=0;
	  mc = new char [128];
	  if(strcmp(mod,"lorentz")==0) act=1.;
	    else if(strcmp(mod,"flat")==0) act=0.;
	    else if(strcmp(mod,"interpole")==0){
		std::fstream inp;
		strcpy(mc,"data/input/mc.dat");
		inp.open(mc,std::ios::in);
		if (!inp.is_open()){
		  std::cerr<<"Error opening file "<<mc<<std::endl;
		  exit(1);
		  }
		while(!inp.eof()){
		  inp.getline (line,900);
		  rows++;
		  }
		rows--;
		inp.close();
		omem=new double [rows];
		reph=new double [rows];
		ieph=new double [rows];
		inp.open(mc, std::ios::in);
		for (int i=0; i<rows; i++){
		  inp>>omem[i]>>reph[i]>>ieph[i];
		  reph[i]=reph[i]-2.220;
		  ieph[i]=ieph[i]+0.12;
		  }
		ach = gsl_interp_accel_alloc ();
		reeph = gsl_spline_alloc (gsl_interp_cspline, rows);
		imeph = gsl_spline_alloc (gsl_interp_cspline, rows);
		gsl_spline_init (reeph, omem, reph, rows);
		gsl_spline_init (imeph, omem, ieph, rows);
		act=66.;
	      }
	    else{
	      std::cout<<"option are: flat, lorentz, interpole"<<std::endl;
	      exit(1);
	      }
	  }

	std::complex<double> drude(double ome){
	  std::complex<double> eps;
	  eps= eps_inf - ome_p2/(ome*(ome+img/tau_d));
	  return eps;
	  }

	std::complex<double> lor_dru(double ome){
	  std::complex<double> eps;
	  eps= eps_inf - ome_p2/(ome*(ome+img/tau_d)) - Deps*ome_L2/((ome*ome-ome_L2)+img*ome/tau_L);
	  return eps;
	  }

	std::complex<double> metal(double ome){
	  std::complex<double> eps;
	  if (lrntz == -1){
	     eps.real(gsl_spline_eval (reeps, ome, acc));
	     eps.imag(gsl_spline_eval (imeps, ome, acc));
	    } else eps= eps_inf - ome_p2/(ome*(ome+img*Gam_d)) - lrntz*Deps*ome_L2/((ome*ome-ome_L2)+img*ome/tau_L);
	  return eps;
	  }
	  
	std::complex<double> confinement(double ome){
	  std::complex<double> dlt;
	  dlt=ome_p2/(ome*(ome+img*Gam_d))-ome_p2/(ome*(ome+img*(Gam_d+Gam)));
	  return dlt;
	  }

	std::complex<double> lorentz(double omega, double omega_o2, double omega_p2, double gamma){
	  std::complex<double> eps;
	  double spe;
	  spe = omega_p2/((omega_o2-omega*omega)*(omega_o2-omega*omega)+gamma*gamma*omega*omega);
	  eps = std::complex<double> (1. + spe*(omega_o2-omega*omega), gamma*omega*spe);
	  return eps;
	  }

	std::complex<double> active(double ome, double epsh){
	  std::complex<double> eps, epsH;
	  if (act!=66.){
	      epsH = std::complex<double> (epsh,0.);
	      eps=epsH-act*G*Dome/(2.*(ome-ome_0)+img*Dome)+(1-act)*G*img;
	      } else {
		eps.real(epsh+enha*gsl_spline_eval (reeph, ome, ach));
		eps.imag(enha*gsl_spline_eval (imeph, ome, ach));
		}
	  kap =-.5*imag(eps)/(sqrt(real(eps)));//1/sqrt(2) // sqrt(.5*(-real(eps)+abs(eps)));
	  gam = 4.*pi*kap*ome/(j2eV*h*cc);
	  enne = gam/(.95*8.e-20);//.95 quantum yeld 8.e-20 cross section
	  return eps;
	  }

double cond1(double ome, double eps2_0, double eps3_0){
    std::complex<double> eps1=metal(ome);
    std::complex<double> eps2=active(ome, eps2_0);
    double rap3=rap*rap*rap;
    double cnd1=2.*((std::real(eps1)-std::real(eps2))*(std::real(eps2)-eps3_0)-(std::imag(eps1)-std::imag(eps2))*std::imag(eps2))*rap3+(std::real(eps2)+2.*eps3_0)*(2.*std::real(eps2)+std::real(eps1))-std::imag(eps2)*(2.*std::imag(eps2)+std::imag(eps1));
    return cnd1;
    }
    
double cond2(double ome, double eps2_0, double eps3_0){
    std::complex<double> eps1=metal(ome);
    std::complex<double> eps2=active(ome, eps2_0);
    double rap3=rap*rap*rap;
    double cnd2=2.*((std::imag(eps1)-std::imag(eps2))*(std::real(eps2)-eps3_0)+std::imag(eps2)*(std::real(eps1)-std::real(eps2)))*rap3+std::imag(eps2)*(2.*std::real(eps2)+std::real(eps1))+
  (2.*std::imag(eps2)+std::imag(eps1))*(std::real(eps2)+2.*eps3_0);
    return cnd2;
    }

	std::complex<double> effective(std::complex<double> alph){
	  std::complex<double> eps;
	  eps=eps3+n*alph/(1.-n*alph/(3.*eps3));
	  return eps;
	  }

	std::complex<double> plrizablty(std::complex<double> eps1, std::complex<double> eps2){
	  std::complex<double> eps_a;
	  std::complex<double> eps_b;
	  std::complex<double> alph;
	  double P=1-rap*rap*rap;
	  eps_a = eps1*(3.-2.*P) + 2.*eps2*P;
	  eps_b = eps1*P + eps2*(3.-P);
	  alph=4.*pi*r2*r2*r2*eps3*((eps2*eps_a-eps3*eps_b)/(eps2*eps_a+2.*eps3*eps_b));
	  return alph;
	  }
	};
