import {
generateHealthReport
}
from "../health/health-reporter";


console.log(

JSON.stringify(
generateHealthReport(),
null,
2
)

);