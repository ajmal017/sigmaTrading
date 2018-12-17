************************************************************
*                                                          *
* Option portfolio optimisation tool                       *
*                                                          *
* Peeter Meos                                              *
* 21. April 2018                                           *
* O? Sigma Research                                        *
*                                                          *
************************************************************
* Write the options file
file opt "Cplex options file" / cplex.opt /;
put opt "Threads  -1" /
        "Parallelmode -1" /;
putclose opt;

scalar
  v_max_pos      Maximum position size for contract
  v_min_theta    Minimum theta desired
  v_multiplier   Contract multiplier
  v_max_trades
  v_trans_cost
  M              Big M /100000000/
;

$gdxin _gams_py_gdb0.gdx
* Now get all that stuff from the GDX
$load v_multiplier v_min_theta
$load v_trans_cost
$load v_max_trades

************************************************************
* Set definitions for the optimisation                     *
************************************************************
set
  s_greeks  List of greeks
  s_names   List of instrument names
  s_month   Contract month sequence
  s_side    Position side              /long, short/
  s_trade   Trade type                 /buy, sell/
  s_dir     Margin direction           /up, down/
  s_opt     Option side                /o_call, o_put/
;

$load s_names s_greeks s_month

set
 s_inst_month(s_names, s_month) Instrument month tuple
;

************************************************************
* Parameter definitions for the optimisation               *
************************************************************
parameter
  p_greeks(s_names, s_greeks) Greeks values for options
  p_y(s_names, s_side)        Existing positions in portfolio
  p_side(s_names, s_opt)      Option sides
  p_days(s_names)             Days until expiry
  p_months(s_names)           Month sequence
;

$load p_greeks p_y p_margin p_side p_spread p_days
$load p_months p_risk

* Initialise instrument month tuple
s_inst_month(s_names, s_month)$(p_months(s_names) = ord(s_month)) = yes;

************************************************************
* Variable definitions for the optimisation                *
************************************************************
free variables
  z     The objective function
;

integer variables
  x(s_names, s_side) New positions to be opened
;

positive variables
  abs_pos(s_names) Absolute position size
  theta_pen        Theta penalty
;

sos1 variables
  dir_pos(s_names, s_side) SOS1 variables to contain total positions
;

binary variables
  b(s_names, s_side) Binary switches for positions and sides
;

************************************************************
* Equation definitions for the optimisation                *
************************************************************
equations
  obj                 Objective function theta maximization
  min_theta           Minimum theta allowed
  dir_breakdown(s_names) Breaks down total position into long and short
  x_sos1(s_names, s_side)
  x_sos1_sum(s_names)
  max_trades          Maximum rebalancing trades allowed
;

$macro pos(s_names) (x(s_names, "long") - x(s_names, "short") \
                  + p_y(s_names, "long") - p_y(s_names, "short"))

$macro pos_l(s_names) (x.l(s_names, "long") - x.l(s_names, "short") \
                  + p_y(s_names, "long") - p_y(s_names, "short"))


************************************************************
* The objective function is transaction minimisation        *
* Direction is minimisation                                *
************************************************************
obj ..
  z
  =e=
** Minimum number of trades, if possible
  v_trans_cost * sum((s_names, s_side), x(s_names, s_side))
;

************************************************************
* Minimum portfolio delta desired                          *
* Add penalty to avoid infeasibilities                     *
************************************************************
min_theta..
    sum(s_names, pos(s_names) * p_greeks(s_names, "theta"))
    =g= v_min_theta - theta_pen;

************************************************************
* Variable to calculate the length of the position         *
************************************************************
dir_breakdown(s_names)..
  x(s_names, "long") - x(s_names, "short")
  +
  p_y(s_names, "long") - p_y(s_names, "short")
  =e=
  dir_pos(s_names, "long") - dir_pos(s_names, "short")
;

************************************************************
* SOS1 constraints for binary indicator variables that show*
* whether a respective position is open                    *
************************************************************
x_sos1(s_names, s_side)..
  x(s_names, s_side) =l= b(s_names, s_side) * M
;

x_sos1_sum(s_names)..
  sum(s_side, b(s_names, s_side)) =l= 1
;

************************************************************
* Maximum number of trades allowed                         *
************************************************************
max_trades..
  sum((s_names, s_side), x(s_names, s_side)) =l= v_max_trades
;

************************************************************
* Compose and solve the model                              *
************************************************************
model spo Portfolio optimisation model /all/;
spo.OptFile = 1;
solve spo minimizing z using mip;

************************************************************
* Postprocessing                                           *
************************************************************
set
  s_age Old and new /old, new/
;

parameters
  total_greeks(s_age, s_greeks)     Aggregated greeks for the portfolio
  pos_greeks(s_names, s_greeks)     Greeks for the portfolio per position
  total_pos(s_names)                Total new portfolio position
  trades(s_names, s_trade)          Trades recommended
  total_margin(s_dir)
  total_margin_old(s_dir)
  pos_risk(s_names, s_dir)          Position value change if prices rise or drop
  total_risk(s_dir)                 Total portfolio value change if prices rise or drop
  monthly_greeks(s_age, s_month, s_greeks) Monthly greek aggregations
;

scalar
  total_initial_margin
  total_initial_margin_old
;

pos_greeks(s_names, s_greeks) =
  pos_l(s_names) * p_greeks(s_names, s_greeks) * v_multiplier;

total_greeks("new", s_greeks)
  = sum(s_names, pos_greeks(s_names, s_greeks));
total_greeks("old", s_greeks)
  = sum(s_names, (p_y(s_names, "long") - p_y(s_names, "short"))
                                           * p_greeks(s_names, s_greeks)
                                           * v_multiplier);
total_pos(s_names) =  pos_l(s_names);

monthly_greeks("new", s_month, s_greeks)
  = sum(s_names$s_inst_month(s_names, s_month),
        pos_greeks(s_names, s_greeks));

monthly_greeks("old", s_month, s_greeks)
  = sum(s_names$s_inst_month(s_names, s_month),
       (p_y(s_names, "long") - p_y(s_names, "short"))
                                           * p_greeks(s_names, s_greeks)
                                           * v_multiplier);

trades(s_names, "buy")$(x.l(s_names, "long") - x.l(s_names, "short") > 0)
  = x.l(s_names, "long") - x.l(s_names, "short");

trades(s_names, "sell")$(x.l(s_names, "short") - x.l(s_names, "long") > 0)
  = x.l(s_names, "short") - x.l(s_names, "long");

* Call and put margins cancel each other out to some degree
total_margin("up") = sum(s_names,
   (-p_margin(s_names, "short")
   * total_pos(s_names)
   * p_side(s_names, "o_call"))$(total_pos(s_names) < 0)
     +
    (p_margin(s_names, "long")
   * total_pos(s_names)
   * p_side(s_names, "o_put"))$(total_pos(s_names) > 0)
);

total_margin("down") = sum(s_names,
    (p_margin(s_names, "long")
   * total_pos(s_names)
   * p_side(s_names, "o_call"))$(total_pos(s_names) > 0)
     +
   (-p_margin(s_names, "short")
   * total_pos(s_names)
   * p_side(s_names, "o_put"))$(total_pos(s_names) < 0)
);

total_margin_old("up") = sum(s_names,
    (p_margin(s_names, "short")
   * p_y(s_names, "short")
   * p_side(s_names, "o_call"))
     +
    (p_margin(s_names, "long")
   * p_y(s_names, "long")
   * p_side(s_names, "o_put"))
);

total_margin_old("down") = sum(s_names,
    (p_margin(s_names, "long")
   * p_y(s_names, "long")
   * p_side(s_names, "o_call"))
     +
    (p_margin(s_names, "short")
   * p_y(s_names, "short")
   * p_side(s_names, "o_put"))
);

total_initial_margin = smax(s_dir, total_margin(s_dir));
total_initial_margin_old = smax(s_dir, total_margin_old(s_dir));

pos_risk(s_names, s_dir) = pos_l(s_names)
                      * p_risk(s_names, s_dir) * v_multiplier
;

total_risk(s_dir) = sum(s_names, pos_l(s_names)
                      * p_risk(s_names, s_dir) * v_multiplier
);


execute_unload "_gams_py_gdb1.gdx"
