<h1> Description </h1>
This is a repo for conducting data analysis on synthetic data. The goal is to conduct analysis on Alzheimer's 


<h2> IPython Notebook </h2>
This contacts a notebook that connects to Google Colab. This is a more visual representation of the code. Google Colab should also be interactive as well. 
<strong> Google Colab </strong> is likely the preferred method for running the code as the enviroment is already configured 


<h2> Scripts </h2>
This is a script verison of the code from the .ipynb file. There are minor differences. Namely, the pip install commands are not included as the syntax varied. For instance, the "!" operator to access the command line from a cell. 
It may be a bit more difficult to configure for your machine. However, I added some config files for build tools to aid in the configuration process. The only issue that one may run into is when installing the statsmodels package. 
 Please run this install command with pip to install the most recent verison of statsmodels and <strong> restart the python runtime enviroment </strong>
 <code>
      pip install statsmodels --upgrade
    </code>
    
 <h3>
  Please note within Scripts there is a tests directory that provides unit testing for the data manipulation questions. 
  </h3>
  The syntax for using the testing suite is the following:
  <code>
      pytest -v -m Question_One
      pytest -v -m Question_Two
      pytest -v -m Question_Three
       ....
  </code>