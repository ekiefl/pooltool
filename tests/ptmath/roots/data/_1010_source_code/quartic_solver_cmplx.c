#include<stdlib.h>
#include<math.h>
#include<stdio.h>
#include<string.h>
#include<signal.h>
#include <complex.h>
#include <unistd.h>
#include <float.h>
#include <time.h>
#define Sqr(x) ((x)*(x))
#ifndef CMPLX
#define CMPLX(x,y) (x)+(y)*I
#endif
const double cubic_rescal_fact_cmplx = 3.488062113727083E+102; //= pow(DBL_MAX,1.0/3.0)/1.618034;
const double quart_rescal_fact_cmplx = 7.156344627944542E+76; // = pow(DBL_MAX,1.0/4.0)/1.618034;
const double macheps_cmplx =2.2204460492503131E-16; // = DBL_EPSILON
double oqs_max2_cmplx(double a, double b)
{
  if (a >= b)
    return a;
  else
    return b;
}
double oqs_max3_cmplx(double a, double b, double c)
{
  double t;
  t = oqs_max2_cmplx(a,b);
  return oqs_max2_cmplx(t,c);
}
void oqs_solve_cubic_analytic_depressed_handle_inf_cmplx(complex double b, complex double c, complex double *sol)
{
  /* find analytically the dominant root of a depressed cubic x^3+b*x+c 
   * where coefficients b and c are large (see sec. 2.2 in the manuscript) */ 
  complex double asol[3], Am, Ap, ApB, AmB, Q, R, A, B, QR, QRSQ, KK, RQ;
  const double PI2=M_PI/2.0, TWOPI=2.0*M_PI;
  double theta, sqrtQr, Ar, Br, QRr, QRSQr, KKr, RQr;
  const double sqrt3=sqrt(3.0)/2.0;
  int arereal=0;
  Q = -b/3.0;
  R = 0.5*c;
  if (R==0)
    {
      *sol=csqrt(-b);
      return;
    }
  if (cimag(Q)==0 && cimag(R)==0)
    {
      arereal=1;
    }
  else
    {
      arereal=0;
    }
  if (arereal)
    {
      if (fabs(creal(Q)) < fabs(creal(R)))
        {
          QRr=creal(Q/R);
          QRSQr=QRr*QRr; 
          KKr=1.0 - creal(Q)*QRSQr;
        }
      else
        {
          RQr = creal(R/Q);
          KKr = copysign(1.0,creal(Q))*(RQr*RQr/creal(Q)-1.0);
        }

      if (KKr < 0.0)
        {
          sqrtQr=sqrt(creal(Q));
          theta = acos((creal(R)/fabs(creal(Q)))/sqrtQr);
          if (theta < PI2) 
            *sol = -2.0*sqrtQr*cos(theta/3.0);
          else 
            *sol = -2.0*sqrtQr*cos((theta+TWOPI)/3.0);
        }
      else
        {
          if (fabs(creal(Q)) < fabs(creal(R)))
            Ar = -copysign(1.0,creal(R))*cbrt(fabs(creal(R))*(1.0+sqrt(KKr)));
          else
            {
              Ar = -copysign(1.0,creal(R))*cbrt(fabs(creal(R))+sqrt(fabs(creal(Q)))*fabs(creal(Q))*sqrt(KKr));
            }
          if (Ar==0.0)
            Br=0.0;
          else
            Br = creal(Q)/Ar;
          *sol = Ar+Br;
        }
    }
  else
    {
      if (cabs(Q) < cabs(R))
        {
          QR=Q/R;
          QRSQ=QR*QR; 
          KK=1.0 - Q*QRSQ;
          Ap = -cpow(R*(1.0+csqrt(KK)), 1.0/3.0);
          Am = -cpow(R*(1.0-csqrt(KK)), 1.0/3.0);
          if (cabs(Ap) > cabs(Am))
            A = Ap;
          else
            {
              A = Am;
            }
        }
      else
        {
          RQ = R/Q;
          KK = RQ*RQ/Q-1.0;
          KK *= Q*Q*Q;
          Ap = -cpow(R+csqrt(KK), 1.0/3.0);
          Am = -cpow(R-csqrt(KK), 1.0/3.0);
          if (cabs(Ap) > cabs(Am))
            A = Ap;
          else
            {
              A = Am;
            }
        }
      if (A==0.0)
        B=0.0;
      else
        B = Q/A;
      *sol = A+B;
      ApB=A+B;
      AmB=A-B;
      asol[0] = ApB; /* this is always largest root even if A=B */
      asol[1] = -0.5*ApB + I*sqrt3*(AmB);
      asol[2] = -0.5*ApB - I*sqrt3*(AmB);
      *sol=asol[0];
      if (cabs(*sol) < cabs(asol[1]))
        *sol=asol[1];
      if (cabs(*sol) < cabs(asol[2]))
        *sol=asol[2];
    }
}
void oqs_solve_cubic_analytic_depressed_cmplx(complex double b, complex double c, complex double *sol)
{
  /* find analytically the dominant root of a depressed cubic x^3+b*x+c 
   * (see sec. 2.2 in the manuscript) */ 
  complex double K, Q, R, Q3, R2, A, B, Ap, Am, asol[3], ApB, AmB;
  int arereal=0;
  double theta, Q3r, R2r, sqrtQr, Ar, Br;
  const double sqrt3=sqrt(3.0)/2.0;
  Q = -b/3.0;
  R = 0.5*c;
  if (cabs(Q) > 1E102 || cabs(R) > 1E154)
    {
      oqs_solve_cubic_analytic_depressed_handle_inf_cmplx(b, c, sol);
      return;
    }
  if (cimag(Q)==0 && cimag(R)==0)
    {
      arereal=1;
      Q3r = creal(Sqr(Q)*Q);
      R2r = creal(Sqr(R));
    }
  else
    {
      arereal=0;
      Q3 = Sqr(Q)*Q;
      R2 = Sqr(R);
    }
  if (arereal)
    {
      if (R2r < Q3r)
        {
          theta = acos(creal(R)/sqrt(Q3r));
          sqrtQr=-2.0*sqrt(creal(Q));
          if (theta < M_PI/2) 
            *sol = sqrtQr*cos(theta/3.0);
          else 
            *sol = sqrtQr*cos((theta+2.0*M_PI)/3.0);
        }
      else
        {
          Ar = -copysign(1.0,creal(R))*pow(fabs(creal(R)) + sqrt(R2r - Q3r),1.0/3.0);
          if (Ar==0.0)
            Br=0.0;
          else
            Br = creal(Q)/Ar;
          *sol = Ar+Br; /* this is always largest root even if A=B */
        }
    }
  else
    {
      K=csqrt(R2 - Q3);
      Ap = -cpow(R + K,1.0/3.0);
      Am = -cpow(R - K,1.0/3.0);
      if (cabs(Ap) > cabs(Am))
        A=Ap;
      else 
        A=Am;
      if (A==0.0)
        B=0.0;
      else
        B = Q/A;
      ApB=A+B;
      AmB=A-B;
      asol[0] = ApB; /* this is always largest root even if A=B */
      asol[1] = -0.5*ApB + I*sqrt3*(AmB);
      asol[2] = -0.5*ApB - I*sqrt3*(AmB);
      *sol=asol[0];
      if (cabs(*sol) < cabs(asol[1]))
        *sol=asol[1];
      if (cabs(*sol) < cabs(asol[2]))
        *sol=asol[2];
    }
}


void oqs_solve_quadratic_cmplx(double a, double b, complex double roots[2])
{ 
  /* find the roots of the real quadratic equation x^2 + a*x + b = 0*/
  double div,sqrtd,diskr,zmax,zmin;
  diskr=a*a-4*b;   
  if(diskr>=0.0)
    {
      if(a>=0.0)
        div=-a-sqrt(diskr);
      else
        div=-a+sqrt(diskr);

      zmax=div/2;

      if(zmax==0.0)
        zmin=0.0;
      else
        zmin=b/zmax;

      roots[0]=CMPLX(zmax,0.0);
      roots[1]=CMPLX(zmin,0.0);
    } 
  else
    {   
      sqrtd = sqrt(-diskr);
      roots[0]=CMPLX(-a/2,sqrtd/2);
      roots[1]=CMPLX(-a/2,-sqrtd/2);      
    }   
}

void oqs_calc_phi0_cmplx(complex double a, complex double b, complex double c, complex double d, complex double *phi0, int scaled)
{
  /* find phi0 as the dominant root of the depressed and shifted cubic 
   * in eq. (79) (see also the discussion in sec. 2.2 of the manuscript) */
  complex double rmax, g,h,gg,hh,aq,bq,cq,dq,s,diskr, sp, sm;
  complex double xxx, gx, x, xold, f, fold, df, xsq;
  complex double ggss, hhss, dqss, aqs, bqs, cqs;
  double rfact, rfactsq;
  double maxtt, diskrr;
  int iter;

  /* eq. (87) */ 
  if (cimag(a)==0 && cimag(b)==0)
    {
      diskrr=creal(9*a*a-24*b);                    
      if(diskrr > 0.0)
        { 
          diskrr=sqrt(diskrr);
          if(creal(a) > 0.0)
            s=-2*creal(b)/(3*a+diskrr);                     
          else
            s=-2*creal(b)/(3*creal(a)-diskrr);                      
        }
      else
        {      
          s=-creal(a)/4;                                    
        }
    }
  else
    {
      diskr=csqrt(9*a*a-24*b);                    
      sp = -3*a+diskr;
      sm = -3*a-diskr;
      if (cabs(sp) > cabs(sm))
        s = 2.0*b/sp;
      else
        s = 2.0*b/sm;
    }
  /* eqs. (83) */
  aq=a+4*s;                                      
  bq=b+3*s*(a+2*s);                              
  cq=c+s*(2*b+s*(3*a+4*s));                      
  dq=d+s*(c+s*(b+s*(a+s)));                      
  gg=bq*bq/9;
  hh=aq*cq;      
  g=hh-4*dq-3*gg;                       /* eq. (85) */                             
  h=(8*dq+hh-2*gg)*bq/3-cq*cq-dq*aq*aq; /* eq. (86) */         
  oqs_solve_cubic_analytic_depressed_cmplx(g, h, &rmax);
  if (isnan(creal(rmax)) || isinf(creal(rmax))||
      isnan(cimag(rmax)) || isinf(cimag(rmax)))

    {
      oqs_solve_cubic_analytic_depressed_handle_inf_cmplx(g, h, &rmax);
      if ((isnan(creal(rmax)) || isinf(creal(rmax))||
           isnan(cimag(rmax)) || isinf(cimag(rmax))) && scaled)
        {
          // try harder: rescale also the depressed cubic if quartic has been already rescaled
          rfact = cubic_rescal_fact_cmplx;
          rfactsq = rfact*rfact;
          ggss = gg/rfactsq;
          hhss = hh/rfactsq;
          dqss = dq/rfactsq;
          aqs = aq/rfact;
          bqs = bq/rfact;
          cqs = cq/rfact;
          ggss=bqs*bqs/9.0;
          hhss=aqs*cqs;  
          g=hhss-4.0*dqss-3.0*ggss;                       
          h=(8.0*dqss+hhss-2.0*ggss)*bqs/3.0-cqs*(cqs/rfact)-(dq/rfact)*aqs*aqs; 
          oqs_solve_cubic_analytic_depressed_cmplx(g, h, &rmax);
          if (isnan(creal(rmax)) || isinf(creal(rmax))||
              isnan(cimag(rmax)) || isinf(cimag(rmax)))
            {
              oqs_solve_cubic_analytic_depressed_handle_inf_cmplx(g, h, &rmax);
            }
          rmax *= rfact;
        }
    }
  /* Newton-Raphson used to refine phi0 (see end of sec. 2.2 in the manuscript) */
  x = rmax;
  xsq=x*x;
  xxx=x*xsq;
  gx=g*x;
  f = x*(xsq + g) + h;
  if (cabs(xxx) > cabs(gx))
    maxtt = cabs(xxx);
  else
    maxtt = cabs(gx);
  if (cabs(h) > maxtt)
    maxtt = cabs(h);
  if (cabs(f) > macheps_cmplx*maxtt)
    {
      for (iter=0; iter < 8; iter++)
        {   
          df =  3.0*xsq + g;
          if (df==0)
            {
              break;
            }
          xold = x;
          x += -f/df;
          fold = f;
          xsq = x*x;
          f = x*(xsq + g) + h;
          if (f==0)
            {
              break;
            } 

          if (cabs(f) >= cabs(fold))
            {
              x = xold;
              break;
            }
        }
    }
  *phi0 = x;
}
double oqs_calc_err_ldlt_cmplx(complex double b, complex double c, complex double d, complex double d2, 
                               complex double l1, complex double l2, complex double l3)
{
  /* Eqs. (29) and (30) in the manuscript */
  double sum;
  sum =  (b==0)?cabs(d2 + l1*l1 + 2.0*l3):cabs(((d2 + l1*l1 + 2.0*l3)-b)/b);
  sum += (c==0)?cabs(2.0*d2*l2 + 2.0*l1*l3):cabs(((2.0*d2*l2 + 2.0*l1*l3)-c)/c);
  sum += (d==0)?cabs(d2*l2*l2 + l3*l3):cabs(((d2*l2*l2 + l3*l3)-d)/d);
  return sum;
}
double oqs_calc_err_abcd_ccmplx(complex double a, complex double b, complex double c, complex double d, 
                                complex double aq, complex double bq, complex double cq, complex double dq)
{
  /* Eqs. (68) and (69) in the manuscript */
  double sum;
  sum = (d==0)?cabs(bq*dq):cabs((bq*dq-d)/d);
  sum += (c==0)?cabs(bq*cq + aq*dq):cabs(((bq*cq + aq*dq) - c)/c);
  sum +=(b==0)?cabs(bq + aq*cq + dq):cabs(((bq + aq*cq + dq) - b)/b);
  sum +=(a==0)?cabs(aq + cq):cabs(((aq + cq) - a)/a);
  return sum;
}
double oqs_calc_err_abc_cmplx(complex double a, complex double b, complex double c, complex double aq, 
                              complex double bq, complex double cq, complex double dq)
{
  /* Eqs. (48)-(51) in the manuscript */
  double sum;
  sum = (c==0)?cabs(bq*cq + aq*dq):cabs(((bq*cq + aq*dq) - c)/c);
  sum +=(b==0)?cabs(bq + aq*cq + dq):cabs(((bq + aq*cq + dq) - b)/b);
  sum +=(a==0)?cabs(aq + cq):cabs(((aq + cq) - a)/a);
  return sum;
}
void oqs_NRabcd_cmplx(double a, double b, double c, double d, double *AQ, double *BQ, double *CQ, double *DQ)
{
  /* Newton-Raphson described in sec. 2.3 of the manuscript for real
   * coefficients a,b,c,d */
  int iter, k1, k2;
  double x02, errf, errfold, xold[4], x[4], dx[4], det, Jinv[4][4], fvec[4], vr[4];
  x[0] = *AQ;
  x[1] = *BQ;
  x[2] = *CQ;
  x[3] = *DQ;
  vr[0] = d;
  vr[1] = c;
  vr[2] = b;
  vr[3] = a;
  fvec[0] = x[1]*x[3] - d;
  fvec[1] = x[1]*x[2] + x[0]*x[3] - c;
  fvec[2] = x[1] + x[0]*x[2] + x[3] - b;
  fvec[3] = x[0] + x[2] - a; 
  errf=0;
  for (k1=0; k1 < 4; k1++)
    {
      errf += (vr[k1]==0)?fabs(fvec[k1]):fabs(fvec[k1]/vr[k1]);
    }
  for (iter = 0; iter < 8; iter++)
    {
      x02 = x[0]-x[2];
      det = x[1]*x[1] + x[1]*(-x[2]*x02 - 2.0*x[3]) + x[3]*(x[0]*x02 + x[3]);
      if (det==0.0)
        break;
      Jinv[0][0] = x02;
      Jinv[0][1] = x[3] - x[1];
      Jinv[0][2] = x[1]*x[2] - x[0]*x[3];
      Jinv[0][3] = -x[1]*Jinv[0][1] - x[0]*Jinv[0][2]; 
      Jinv[1][0] = x[0]*Jinv[0][0] + Jinv[0][1];
      Jinv[1][1] = -x[1]*Jinv[0][0];
      Jinv[1][2] = -x[1]*Jinv[0][1];   
      Jinv[1][3] = -x[1]*Jinv[0][2];
      Jinv[2][0] = -Jinv[0][0];
      Jinv[2][1] = -Jinv[0][1];
      Jinv[2][2] = -Jinv[0][2];
      Jinv[2][3] = Jinv[0][2]*x[2] + Jinv[0][1]*x[3];
      Jinv[3][0] = -x[2]*Jinv[0][0] - Jinv[0][1];
      Jinv[3][1] = Jinv[0][0]*x[3];
      Jinv[3][2] = x[3]*Jinv[0][1];
      Jinv[3][3] = x[3]*Jinv[0][2];
      for (k1=0; k1 < 4; k1++)
        {
          dx[k1] = 0;
          for (k2=0; k2 < 4; k2++)
            dx[k1] += Jinv[k1][k2]*fvec[k2];
        }
      for (k1=0; k1 < 4; k1++)
        xold[k1] = x[k1];

      for (k1=0; k1 < 4; k1++)
        {
          x[k1] += -dx[k1]/det;
        }
      fvec[0] = x[1]*x[3] - d;
      fvec[1] = x[1]*x[2] + x[0]*x[3] - c;
      fvec[2] = x[1] + x[0]*x[2] + x[3] - b;
      fvec[3] = x[0] + x[2] - a; 
      errfold = errf;
      errf=0;
      for (k1=0; k1 < 4; k1++)
        {
          errf += (vr[k1]==0)?fabs(fvec[k1]):fabs(fvec[k1]/vr[k1]);
        }
      if (errf==0)
        break;
      if (errf >= errfold)
        {
          for (k1=0; k1 < 4; k1++)
            x[k1] = xold[k1];
          break;
        }
    }
  *AQ=x[0];
  *BQ=x[1];
  *CQ=x[2];
  *DQ=x[3];
}
void NRabcdCCmplx(complex double a, complex double b, complex double c, complex double d, 
                  complex double *AQ, complex double *BQ, complex double *CQ, complex double *DQ)
{
  /* Newton-Raphson described in sec. 2.3 of the manuscript for complex
   * coefficients a,b,c,d */
  int iter, k1, k2;
  complex double x02, xold[4], dx[4], x[4], det, Jinv[4][4], fvec[4], vr[4];
  double errf, errfold;
  x[0] = *AQ;
  x[1] = *BQ;
  x[2] = *CQ;
  x[3] = *DQ;
  vr[0] = d;
  vr[1] = c;
  vr[2] = b;
  vr[3] = a;
  fvec[0] = x[1]*x[3] - d;
  fvec[1] = x[1]*x[2] + x[0]*x[3] - c;
  fvec[2] = x[1] + x[0]*x[2] + x[3] - b;
  fvec[3] = x[0] + x[2] - a; 
  errf=0;
  for (k1=0; k1 < 4; k1++)
    {
      errf += (vr[k1]==0)?cabs(fvec[k1]):cabs(fvec[k1]/vr[k1]);
    }

  if (errf==0)
    return;

  for (iter = 0; iter < 8; iter++)
    {
      x02 = x[0]-x[2];
      det = x[1]*x[1] + x[1]*(-x[2]*x02 - 2.0*x[3]) + x[3]*(x[0]*x02 + x[3]);
      if (det==0.0)
        break;
      Jinv[0][0] = x02;
      Jinv[0][1] = x[3] - x[1];
      Jinv[0][2] = x[1]*x[2] - x[0]*x[3];
      Jinv[0][3] = -x[1]*Jinv[0][1] - x[0]*Jinv[0][2]; 
      Jinv[1][0] = x[0]*Jinv[0][0] + Jinv[0][1];
      Jinv[1][1] = -x[1]*Jinv[0][0];
      Jinv[1][2] = -x[1]*Jinv[0][1];   
      Jinv[1][3] = -x[1]*Jinv[0][2];
      Jinv[2][0] = -Jinv[0][0];
      Jinv[2][1] = -Jinv[0][1];
      Jinv[2][2] = -Jinv[0][2];
      Jinv[2][3] = Jinv[0][2]*x[2] + Jinv[0][1]*x[3];
      Jinv[3][0] = -x[2]*Jinv[0][0] - Jinv[0][1];
      Jinv[3][1] = Jinv[0][0]*x[3];
      Jinv[3][2] = x[3]*Jinv[0][1];
      Jinv[3][3] = x[3]*Jinv[0][2];
      for (k1=0; k1 < 4; k1++)
        {
          dx[k1] = 0;
          for (k2=0; k2 < 4; k2++)
            dx[k1] += Jinv[k1][k2]*fvec[k2];
        }
      for (k1=0; k1 < 4; k1++)
        xold[k1] = x[k1];

      for (k1=0; k1 < 4; k1++)
        {
          x[k1] += -dx[k1]/det;
        }

      fvec[0] = x[1]*x[3] - d;
      fvec[1] = x[1]*x[2] + x[0]*x[3] - c;
      fvec[2] = x[1] + x[0]*x[2] + x[3] - b;
      fvec[3] = x[0] + x[2] - a; 

      errfold = errf;
      errf=0;
      for (k1=0; k1 < 4; k1++)
        {
          errf += (vr[k1]==0)?cabs(fvec[k1]):cabs(fvec[k1]/vr[k1]);
        }
      if (errf==0)
        break;
      if (errf >= errfold)
        {
          for (k1=0; k1 < 4; k1++)
            x[k1] = xold[k1];
          break;
        }
    }
  *AQ=x[0];
  *BQ=x[1];
  *CQ=x[2];
  *DQ=x[3];
}
void oqs_quartic_solver_cmplx(complex double coeff[5], complex double roots[4])      
{
  /* USAGE:
   *
   * This routine calculates the roots of the quartic equation (coeff[] may be complex here)
   *
   * coeff[4]*x^4 + coeff[3]*x^3 + coeff[2]*x^2 + coeff[1]*x + coeff[0] = 0
   * 
   * if coeff[4] != 0 
   *
   * the four roots will be stored in the complex array roots[] 
   *
   * */
  complex double acx1, bcx1, ccx1, dcx1,acx,bcx,cdiskr,zx1,zx2,zxmax,zxmin, ccx, dcx;
  complex double l2m[12], d2m[12], bl311, dml3l3; 
  complex double a,b,c,d,phi0,d2,d3,l1,l2,l3,acxv[3],ccxv[3],gamma,del2,qroots[2];
  double res[12], resmin, err0, err1;
  double errmin, errv[3];
  int k1, k, kmin, nsol;
  double aq, bq, cq, dq;
  double rfactsq, rfact=1.0;
  if (coeff[4]==0.0)
    {
      printf("That's not a quartic!\n");
      return;
    }
  a=coeff[3]/coeff[4];
  b=coeff[2]/coeff[4];
  c=coeff[1]/coeff[4];
  d=coeff[0]/coeff[4];
  oqs_calc_phi0_cmplx(a,b,c,d,&phi0,0);
  // simple polynomial rescaling
  if (isnan(creal(phi0))||isinf(creal(phi0))||
      isnan(cimag(phi0))||isinf(cimag(phi0)))
    {
      rfact = quart_rescal_fact_cmplx;
      a /= rfact;
      rfactsq = rfact*rfact;
      b /= rfactsq;
      c /= rfactsq*rfact;
      d /= rfactsq*rfactsq;
      oqs_calc_phi0_cmplx(a,b,c,d,&phi0, 1);
    }

  l1=a/2;        /* eq. (16) */                                        
  l3=b/6+phi0/2; /* eq. (18) */                                
  del2=c-a*l3;   /* defined just after eq. (27) */                               
  nsol=0;
  bl311 =2.*b/3.-phi0-l1*l1; /* This is d2 as defined in eq. (20)*/ 
  dml3l3 = d-l3*l3;          /* This is d3 as defined in eq. (15) with d2=0 */
  /* Three possible solutions for d2 and l2 (see eqs. (28)) and discussion which follows) */
  if (bl311!=0.0)
    {
      d2m[nsol] = bl311;  
      l2m[nsol] = del2/(2.0*d2m[nsol]);   
      res[nsol] = oqs_calc_err_ldlt_cmplx(b,c,d,d2m[nsol], l1, l2m[nsol], l3);
      nsol++;
    }
  if (del2!=0)
    {
      l2m[nsol]=2*dml3l3/del2;
      if (l2m[nsol]!=0)
        {
          d2m[nsol]=del2/(2*l2m[nsol]);
          res[nsol] = oqs_calc_err_ldlt_cmplx(b,c,d,d2m[nsol], l1, l2m[nsol], l3);
          nsol++;
        }

      d2m[nsol] = bl311;
      l2m[nsol] = 2.0*dml3l3/del2;
      res[nsol] = oqs_calc_err_ldlt_cmplx(b,c,d,d2m[nsol], l1, l2m[nsol], l3);
      nsol++;
    }
  if (nsol==0)
    {
      l2=d2=0.0;
    }
  else
    {
      /* we select the (d2,l2) pair which minimizes errors */
      for (k1=0; k1 < nsol; k1++)
        {
          if (k1==0 || res[k1] < resmin)
            {
              resmin = res[k1];
              kmin = k1;        
            }
        }
      d2 = d2m[kmin];
      l2 = l2m[kmin];
    }
  /* Case I eqs. (37)-(40) */
  gamma=csqrt(-d2);                               
  acx=l1+gamma;                                  
  bcx=l3+gamma*l2;                              
  ccx=l1-gamma;                                
  dcx=l3-gamma*l2;                            
  if(cabs(dcx) < cabs(bcx))
    dcx=d/bcx;     
  else if(cabs(dcx) > cabs(bcx))
    bcx=d/dcx;    
  if (cabs(acx) < cabs(ccx))
    {
      nsol=0;
      if (dcx !=0)
        {
          acxv[nsol] = (c - bcx*ccx)/dcx;   /* see eqs. (47) */
          errv[nsol]=oqs_calc_err_abc_cmplx(a, b, c, acxv[nsol], bcx, ccx, dcx);
          nsol++;
        }
      if (ccx != 0) 
        {
          acxv[nsol] = (b - dcx - bcx)/ccx;  /* see eqs. (47) */
          errv[nsol] = oqs_calc_err_abc_cmplx(a, b, c, acxv[nsol], bcx, ccx, dcx);
          nsol++;
        }
      acxv[nsol] = a - ccx;                  /* see eqs. (47) */ 
      errv[nsol] = oqs_calc_err_abc_cmplx(a, b, c, acxv[nsol], bcx, ccx, dcx);
      nsol++;
      /* we select the value of acx (i.e. alpha1 in the manuscript) which minimizes errors */
      for (k=0; k < nsol; k++)
        {
          if (k==0 || errv[k] < errmin)
            {
              kmin = k;
              errmin = errv[k];
            }
        }
      acx = acxv[kmin];
    }
  else 
    {
      nsol = 0;
      if (bcx != 0)
        { 
          ccxv[nsol] = (c - acx*dcx)/bcx;      /* see eqs. (53) */
          errv[nsol] = oqs_calc_err_abc_cmplx(a, b, c, acx, bcx, ccxv[nsol], dcx);
          nsol++;
        }
      if (acx != 0)
        {
          ccxv[nsol] = (b - bcx - dcx)/acx;    /* see eqs. (53) */
          errv[nsol] = oqs_calc_err_abc_cmplx(a, b, c, acx, bcx, ccxv[nsol], dcx);
          nsol++;
        }
      ccxv[nsol] = a - acx;                    /* see eqs. (53) */
      errv[nsol] = oqs_calc_err_abc_cmplx(a, b, c, acx, bcx, ccxv[nsol], dcx);
      nsol++;     
      /* we select the value of ccx (i.e. alpha2 in the manuscript) which minimizes errors */
      for (k=0; k < nsol; k++)
        {
          if (k==0 || errv[k] < errmin)
            {
              kmin = k;
              errmin = errv[k];
            }
        }
      ccx = ccxv[kmin];
    }
  /* Case III: d2 is 0 or approximately 0 (in this case check which solution is better) */
  if (cabs(d2) <= macheps_cmplx*oqs_max3_cmplx(cabs(2.*b/3.), cabs(phi0), cabs(l1*l1))) 
    {
      d3 = d - l3*l3;
      err0 = oqs_calc_err_abcd_ccmplx(a, b, c, d, acx, bcx, ccx, dcx);
      acx1 = l1;  
      bcx1 = l3 + csqrt(-d3);
      ccx1 = l1;
      dcx1 = l3 - csqrt(-d3);

      if(cabs(dcx1) < cabs(bcx1)) 
        dcx1=d/bcx1;                                        
      else if(cabs(dcx1) > cabs(bcx1))
        bcx1=d/dcx1;                                       
      err1 = oqs_calc_err_abcd_ccmplx(a, b, c, d, acx1, bcx1, ccx1, dcx1);
      if (d2==0 || err1 < err0)
        {
          acx = acx1;
          bcx = bcx1;
          ccx = ccx1;
          dcx = dcx1;
        }
    }
  if (cimag(acx)==0 && cimag(bcx)==0 && cimag(ccx)==0 && cimag(dcx)==0)
    {
      /* if acx, bcx, ccx and dxc are all real do calculations with real numbers... */
      aq=creal(acx);
      bq=creal(bcx);
      cq=creal(ccx);
      dq=creal(dcx);
      oqs_NRabcd_cmplx(creal(a),creal(b),creal(c),creal(d),&aq,&bq,&cq,&dq);      
      oqs_solve_quadratic_cmplx(aq,bq,qroots);
      roots[0]=qroots[0];
      roots[1]=qroots[1];        
      oqs_solve_quadratic_cmplx(cq,dq,qroots);
      roots[2]=qroots[0];
      roots[3]=qroots[1];
    }
  else
    {
      /* first refine the coefficient through a Newton-Raphson */
      NRabcdCCmplx(a,b,c,d,&acx,&bcx,&ccx,&dcx);
      /* finally calculate the roots as roots of p1(x) and p2(x) (see end of sec. 2.1) */
      cdiskr=csqrt(acx*acx-4.0*bcx);
      zx1 = -0.5*(acx+cdiskr);
      zx2 = -0.5*(acx-cdiskr);
      if (cabs(zx1) > cabs(zx2))
        zxmax = zx1;
      else
        zxmax = zx2;
      if (zxmax==0)
        zxmin=0;
      else
        zxmin = bcx/zxmax;
      roots[0] = zxmax;
      roots[1] = zxmin;
      cdiskr=csqrt(ccx*ccx-4.0*dcx);
      zx1 = -0.5*(ccx+cdiskr);
      zx2 = -0.5*(ccx-cdiskr);
      if (cabs(zx1) > cabs(zx2))
        zxmax = zx1;
      else
        zxmax = zx2;
      if (zxmax==0)
        zxmin=0;
      else
        zxmin = dcx/zxmax;
      roots[2]= zxmax;
      roots[3]= zxmin;
    }
  if (rfact!=1.0)
    {
      for (k=0; k < 4; k++)
        roots[k] *= rfact;
    }
}
